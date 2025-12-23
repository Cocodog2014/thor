"""Market Open Grading logic (API module)."""

import logging
import os
import threading
import time
from decimal import Decimal

from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)

_GRADER_THREAD: threading.Thread | None = None
_GRADER_THREAD_LOCK = threading.Lock()
_CONTROL_MARKET_CACHE = {"timestamp": None, "is_open": True}


def _grade_pending_once() -> None:
	"""Grade all pending sessions once (no loop)."""
	if not _any_control_markets_open():
		return

	pending_sessions = MarketSession.objects.filter(wndw="PENDING")

	if pending_sessions.exists():
		logger.debug("Grading %d pending sessions...", pending_sessions.count())

		for session in pending_sessions:
			grader.grade_session(session)


def _any_control_markets_open() -> bool:
	cache_t = _CONTROL_MARKET_CACHE["timestamp"]
	now = timezone.now()
	if cache_t and (now - cache_t).total_seconds() < 5:
		return _CONTROL_MARKET_CACHE["is_open"]

	try:
		from GlobalMarkets.models.market import Market

		is_open = Market.objects.filter(is_control_market=True, is_active=True, status="OPEN").exists()
	except Exception:
		logger.debug("GlobalMarkets availability check failed; assuming markets open.", exc_info=True)
		is_open = True

	_CONTROL_MARKET_CACHE["timestamp"] = now
	_CONTROL_MARKET_CACHE["is_open"] = is_open
	return is_open


class MarketGrader:
	"""Continuously evaluates open trades for all futures."""

	def __init__(self, check_interval: float = 0.5):
		self.check_interval = check_interval
		self.running = False

	def get_current_price(self, symbol: str, signal: str) -> Decimal | None:
		try:
			if symbol == "TOTAL":
				redis_key = "YM"
			elif symbol == "DX":
				redis_key = "$DXY"
			else:
				redis_key = symbol.lstrip("/")

			data = live_data_redis.get_latest_quote(redis_key)

			if not data:
				logger.warning("No Redis data for %s (mapped key: %s)", symbol, redis_key)
				return None

			if signal in ["BUY", "STRONG_BUY"]:
				price = data.get("bid")
			elif signal in ["SELL", "STRONG_SELL"]:
				price = data.get("ask")
			else:
				return None

			return Decimal(str(price)) if price is not None else None

		except Exception as exc:  # noqa: BLE001
			logger.error("Redis price error for %s: %s", symbol, exc, exc_info=True)
			return None

	def grade_session(self, session: MarketSession) -> bool:
		if session.wndw != "PENDING":
			return True

		if not session.entry_price or not session.target_high or not session.target_low:
			logger.debug(
				"⚠ %s (Session #%s) → NEUTRAL: missing entry=%s, target_h=%s, target_l=%s",
				session.future,
				session.session_number,
				session.entry_price,
				session.target_high,
				session.target_low,
			)
			session.wndw = "NEUTRAL"
			session.save(update_fields=["wndw"])
			return True

		if session.bhs in ["HOLD", None, ""]:
			logger.debug(
				"⚠ %s (Session #%s) → NEUTRAL: signal=%s (no trade)",
				session.future,
				session.session_number,
				session.bhs,
			)
			session.wndw = "NEUTRAL"
			session.save(update_fields=["wndw"])
			return True

		current_price = self.get_current_price(session.future, session.bhs)
		if current_price is None:
			logger.debug(
				"⏸ %s (Session #%s) → no price available yet (signal=%s)",
				session.future,
				session.session_number,
				session.bhs,
			)
			return False

		worked = False
		didnt_work = False
		hit_type = None

		if session.bhs in ["BUY", "STRONG_BUY"]:
			target = session.target_high
			stop = session.target_low

			if current_price >= target:
				worked = True
				hit_type = "TARGET"
			elif current_price <= stop:
				didnt_work = True
				hit_type = "STOP"

		elif session.bhs in ["SELL", "STRONG_SELL"]:
			target = session.target_low
			stop = session.target_high

			if current_price <= target:
				worked = True
				hit_type = "TARGET"
			elif current_price >= stop:
				didnt_work = True
				hit_type = "STOP"

		if not worked and not didnt_work:
			return False

		now = timezone.now()
		update_fields = ["wndw"]

		if session.target_hit_at is None:
			session.target_hit_at = now
			session.target_hit_price = current_price
			session.target_hit_type = hit_type
			update_fields.extend(["target_hit_at", "target_hit_price", "target_hit_type"])

		if worked:
			session.wndw = "WORKED"
			verb = "WORKED"
		else:
			session.wndw = "DIDNT_WORK"
			verb = "DIDN'T WORK"

		session.save(update_fields=update_fields)

		logger.info(
			"✅ %s (Session #%s) %s at ~%s [hit_type=%s]",
			session.future,
			session.session_number,
			verb,
			current_price,
			hit_type,
		)
		return True

	def run_grading_loop(self):
		logger.info("Starting Market Open Grader (interval: %ss)", self.check_interval)
		self.running = True

		while self.running:
			try:
				if not _any_control_markets_open():
					time.sleep(self.check_interval)
					continue

				_grade_pending_once()
				time.sleep(self.check_interval)

			except KeyboardInterrupt:
				logger.info("Grading loop interrupted by user")
				self.running = False
				break

			except Exception as exc:  # noqa: BLE001
				logger.error("Grading loop error: %s", exc, exc_info=True)
				time.sleep(self.check_interval)

		logger.info("Market Open Grader stopped")

	def stop(self):
		logger.info("Stopping Market Open Grader...")
		self.running = False


grade_interval_seconds = 0.5
grader = MarketGrader(check_interval=grade_interval_seconds)


def start_grading_service(*, blocking: bool = False) -> bool:
	if os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower() == "heartbeat":
		logger.info("Heartbeat scheduler active; skipping legacy MarketGrader thread")
		return False

	if blocking:
		logger.info("MarketGrader starting in blocking mode.")
		grader.run_grading_loop()
		return True

	global _GRADER_THREAD
	with _GRADER_THREAD_LOCK:
		if _GRADER_THREAD and _GRADER_THREAD.is_alive():
			logger.info("MarketGrader already running; skip new start.")
			return False

		thread = threading.Thread(target=grader.run_grading_loop, name="MarketGraderLoop", daemon=True)
		thread.start()
		_GRADER_THREAD = thread
		logger.info("MarketGrader background thread started.")
		return True


def stop_grading_service(*, wait: bool = False):
	global _GRADER_THREAD
	grader.stop()
	if not wait:
		return

	thread = _GRADER_THREAD
	if thread and thread.is_alive():
		thread.join(timeout=10)

	if thread and not thread.is_alive():
		with _GRADER_THREAD_LOCK:
			if _GRADER_THREAD is thread:
				_GRADER_THREAD = None


__all__ = ["start_grading_service", "stop_grading_service", "MarketGrader", "grader", "_grade_pending_once"]
