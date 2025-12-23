"""Market Open Capture - single-table design.

Captures futures data at market open using the same enrichment pipeline as the
live RTD endpoint. Creates MarketSession rows per market open (one per future +
TOTAL).
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ThorTrading.config.symbols import FUTURES_SYMBOLS
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.indicators import compute_targets_for_symbol
from ThorTrading.services.analytics.backtest_stats import compute_backtest_stats_for_country_future
from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.services.sessions.counters import CountryFutureCounter
from ThorTrading.services.sessions.analytics.wndw_totals import CountryFutureWndwTotalsService
from ThorTrading.services.sessions.metrics import MarketOpenMetric
from ThorTrading.services.quotes import get_enriched_quotes_with_composite

logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
	"""Captures futures data at market open - matches RTD endpoint logic."""

	def get_next_session_number(self):
		last = MarketSession.objects.order_by("-session_number").first()
		return (last.session_number + 1) if last else 1

	def safe_decimal(self, val):
		if val in (None, "", ""):
			return None
		try:
			return Decimal(str(val))
		except Exception:  # noqa: BLE001
			return None

	def safe_int(self, val):
		if val in (None, "", ""):
			return None
		try:
			return int(val)
		except Exception:  # noqa: BLE001
			try:
				return int(float(val))
			except Exception:  # noqa: BLE001
				return None

	def create_session_for_future(self, symbol, row, session_number, capture_group, time_info, country, composite_signal):
		"""Create one MarketSession row for a single future."""

		ext = row.get("extended_data", {})

		data = {
			"session_number": session_number,
			"capture_group": capture_group,
			"year": time_info["year"],
			"month": time_info["month"],
			"date": time_info["date"],
			"day": time_info["day"],
			"country": country,
			"future": symbol,
			"captured_at": timezone.now(),
			"last_price": self.safe_decimal(row.get("last")),
			"ask_price": self.safe_decimal(row.get("ask")),
			"ask_size": self.safe_int(row.get("ask_size")),
			"bid_price": self.safe_decimal(row.get("bid")),
			"bid_size": self.safe_int(row.get("bid_size")),
			"volume": self.safe_int(row.get("volume")),
			"spread": self.safe_decimal(row.get("spread")),
			"open_price_24h": self.safe_decimal(row.get("open_price")),
			"prev_close_24h": self.safe_decimal(row.get("close_price") or row.get("previous_close")),
			"open_prev_diff_24h": self.safe_decimal(row.get("open_prev_diff")),
			"open_prev_pct_24h": self.safe_decimal(row.get("open_prev_pct")),
			"low_24h": self.safe_decimal(row.get("low_price")),
			"high_24h": self.safe_decimal(row.get("high_price")),
			"range_diff_24h": self.safe_decimal(row.get("range_diff")),
			"range_pct_24h": self.safe_decimal(row.get("range_pct")),
			"low_52w": self.safe_decimal(ext.get("low_52w")),
			"low_pct_52w": self.safe_decimal(ext.get("low_pct_52w") or ext.get("low_pct_52")),
			"high_52w": self.safe_decimal(ext.get("high_52w")),
			"range_52w": self.safe_decimal(ext.get("range_52w") or ext.get("week_52_range_high_low")),
			"range_pct_52w": self.safe_decimal(ext.get("range_pct_52w") or ext.get("week_52_range_percent")),
			"high_pct_52w": self.safe_decimal(ext.get("high_pct_52w") or ext.get("high_pct_52")),
			"bhs": (ext.get("signal") or "").upper() if ext.get("signal") else "",
			"weight": self.safe_int(ext.get("signal_weight")),
		}

		data["entry_price"] = None
		data["target_high"] = None
		data["target_low"] = None

		individual_signal = data["bhs"]
		if individual_signal and individual_signal not in ["HOLD", ""]:
			if individual_signal in ["BUY", "STRONG_BUY"]:
				data["entry_price"] = data.get("ask_price")
			elif individual_signal in ["SELL", "STRONG_SELL"]:
				data["entry_price"] = data.get("bid_price")
			entry = data["entry_price"]
			if entry:
				high, low = compute_targets_for_symbol(symbol, entry)
				data["target_high"] = high
				data["target_low"] = low

		wlow = data.get("low_52w")
		whigh = data.get("high_52w")
		last_price = data.get("last_price")
		if wlow is not None:
			try:
				if last_price:
					data["low_pct_52w"] = ((last_price - wlow) / last_price) * Decimal("100")
			except Exception:  # noqa: BLE001
				pass

		if whigh is not None:
			try:
				if last_price:
					data["high_pct_52w"] = ((whigh - last_price) / last_price) * Decimal("100")
			except Exception:  # noqa: BLE001
				pass

		if wlow is not None and whigh is not None:
			try:
				data["range_52w"] = whigh - wlow
				if last_price:
					data["range_pct_52w"] = ((whigh - wlow) / last_price) * Decimal("100")
			except Exception:  # noqa: BLE001
				pass

		try:
			stats = compute_backtest_stats_for_country_future(
				country=country,
				future=symbol,
				as_of=data["captured_at"],
			)
			data.update(stats)
		except Exception as exc:  # noqa: BLE001
			logger.warning("Backtest stats failed for %s: %s", symbol, exc)

		try:
			session = MarketSession.objects.create(**data)
			_country_future_counter.assign_sequence(session)
			logger.debug("Created %s session: %s", symbol, session.last_price)
			return session
		except Exception as exc:  # noqa: BLE001
			logger.error("Session creation failed for %s: %s", symbol, exc, exc_info=True)
			return None

	def create_session_for_total(self, composite, session_number, capture_group, time_info, country, ym_entry_price=None):
		"""Create one MarketSession row for TOTAL composite."""

		composite_signal = (composite.get("composite_signal") or "HOLD").upper()

		data = {
			"session_number": session_number,
			"capture_group": capture_group,
			"year": time_info["year"],
			"month": time_info["month"],
			"date": time_info["date"],
			"day": time_info["day"],
			"country": country,
			"future": "TOTAL",
			"captured_at": timezone.now(),
			"weighted_average": self.safe_decimal(composite.get("avg_weighted")),
			"instrument_count": composite.get("count") or 11,
			"bhs": composite_signal,
			"weight": composite.get("signal_weight_sum"),
		}

		if ym_entry_price is not None and composite_signal not in ["HOLD", ""]:
			data["entry_price"] = ym_entry_price
			high, low = compute_targets_for_symbol("YM", ym_entry_price)
			data["target_high"] = high
			data["target_low"] = low

		try:
			stats = compute_backtest_stats_for_country_future(
				country=country,
				future="TOTAL",
				as_of=data["captured_at"],
			)
			data.update(stats)
		except Exception as exc:  # noqa: BLE001
			logger.warning("Backtest stats failed for TOTAL: %s", exc)

		try:
			session = MarketSession.objects.create(**data)
			_country_future_counter.assign_sequence(session)
			if data.get("weighted_average"):
				logger.info("TOTAL session: %.4f -> %s", data["weighted_average"], composite_signal)
			else:
				logger.info("TOTAL: %s", composite_signal)
			return session
		except Exception as exc:  # noqa: BLE001
			logger.error("TOTAL session creation failed: %s", exc, exc_info=True)
			return None

	@transaction.atomic
	def capture_market_open(self, market):
		display_country = getattr(market, "country", None)
		country_code = normalize_country_code(display_country) or display_country

		if not getattr(market, "enable_futures_capture", True):
			logger.info("Futures capture disabled for %s; skipping.", country_code or display_country or "?")
			return None
		if not getattr(market, "enable_open_capture", True):
			logger.info("Open capture disabled for %s; skipping.", country_code or display_country or "?")
			return None
		try:
			logger.info("Capturing %s market open...", country_code or display_country or "?")

			enriched, composite = get_enriched_quotes_with_composite()
			if not enriched:
				logger.error("No enriched rows for %s", country_code or display_country or "?")
				return None

			allowed_symbols = {s.lstrip("/") for s in FUTURES_SYMBOLS}
			filtered = []
			dropped_symbols = []
			for r in enriched:
				symbol = (r.get("instrument", {}) or {}).get("symbol") or ""
				base_symbol = symbol.lstrip("/")
				if base_symbol not in allowed_symbols:
					continue

				row_country_raw = r.get("country")
				row_country = normalize_country_code(row_country_raw) if row_country_raw else None
				if not row_country:
					dropped_symbols.append(base_symbol)
					continue

				if row_country != (country_code or display_country):
					continue

				filtered.append(r)

			enriched = filtered
			if not enriched:
				logger.error(
					"No enriched rows for %s after country/symbol filter%s",
					country_code or display_country or "?",
					f"; dropped_missing_country={dropped_symbols}" if dropped_symbols else "",
				)
				return None
			composite_signal = (composite.get("composite_signal") or "HOLD").upper()

			time_info = market.get_current_market_time()
			try:
				sym_list = [r.get("instrument", {}).get("symbol") for r in enriched]
				logger.info(
					"MarketOpenCapture %s %04d-%02d-%02d - enriched count=%s, symbols=%s",
					country_code or display_country or "?",
					time_info["year"],
					time_info["month"],
					time_info["date"],
					len(enriched),
					sym_list,
				)
			except Exception:  # noqa: BLE001
				logger.info(
					"MarketOpenCapture %s %04d-%02d-%02d - enriched count=%s",
					country_code or display_country or "?",
					time_info["year"],
					time_info["month"],
					time_info["date"],
					len(enriched),
				)
			session_number = self.get_next_session_number()
			with transaction.atomic():
				last_group_val = (
					MarketSession.objects.exclude(capture_group__isnull=True)
					.aggregate(max_group=Max("capture_group"))
					.get("max_group")
				) or 0
				capture_group = int(last_group_val) + 1

			sessions_created = []
			failures = []
			ym_entry_price = None
			for row in enriched:
				symbol = row["instrument"]["symbol"]
				session = self.create_session_for_future(
					symbol,
					row,
					session_number,
					capture_group,
					time_info,
					country_code or display_country,
					composite_signal,
				)
				if session:
					sessions_created.append(session)
				else:
					failures.append(symbol)
				base_symbol = symbol.lstrip("/").upper()
				if base_symbol == "YM" and composite_signal not in ["HOLD", ""]:
					if composite_signal in ["BUY", "STRONG_BUY"]:
						ym_entry_price = self.safe_decimal(row.get("ask"))
					elif composite_signal in ["SELL", "STRONG_SELL"]:
						ym_entry_price = self.safe_decimal(row.get("bid"))

			total_session = self.create_session_for_total(
				composite,
				session_number,
				capture_group,
				time_info,
				country_code or display_country,
				ym_entry_price=ym_entry_price,
			)
			if total_session:
				sessions_created.append(total_session)

			try:
				MarketOpenMetric.update_for_capture_group(capture_group)
			except Exception as metrics_error:  # noqa: BLE001
				logger.warning(
					"market_open refresh failed for session %s: %s",
					session_number,
					metrics_error,
					exc_info=True,
				)

			try:
				_country_future_wndw_service.update_for_capture_group(
					capture_group=capture_group,
					country=country_code or display_country,
				)
			except Exception as stats_error:  # noqa: BLE001
				logger.warning(
					"Failed country/future WNDW totals refresh after capture %s: %s",
					session_number,
					stats_error,
					exc_info=True,
				)

			logger.info(
				"Capture complete: %s Session #%s, created=%s%s",
				country_code or display_country or "?",
				session_number,
				len(sessions_created),
				(f", failures={failures}" if failures else ""),
			)
			return sessions_created[0] if sessions_created else None

		except Exception as exc:  # noqa: BLE001
			logger.error("Capture failed for %s: %s", country_code or display_country or "?", exc, exc_info=True)
			return None


_service = MarketOpenCaptureService()
_country_future_counter = CountryFutureCounter()
_country_future_wndw_service = CountryFutureWndwTotalsService()


def capture_market_open(market):
	return _service.capture_market_open(market)


__all__ = ["capture_market_open", "MarketOpenCaptureService"]
