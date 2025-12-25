from __future__ import annotations
import logging
import os
import threading
from ThorTrading.GlobalMarketGate.global_market_gate import session_tracking_allowed
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.integrations.accounts.snapshots import trigger_daily_account_snapshots
from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.services.intraday.flush import flush_closed_bars
from ThorTrading.services.intraday_supervisor.session_volume import update_session_volume_for_country
from ThorTrading.services.sessions.metrics import MarketCloseMetric, MarketRangeMetric
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)
_log_level_name = os.getenv("THOR_INTRADAY_LOG_LEVEL", "INFO").upper()
_log_level_value = getattr(logging, _log_level_name, logging.INFO)
logger.setLevel(_log_level_value)


SNAPSHOT_LOCK_PREFIX = "thor:account_snapshot_eod:"
SNAPSHOT_LOCK_TTL_SECONDS = 60 * 60 * 48  # 48h safety window


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning("Invalid int for %s=%s; using default %s", name, val, default)
        return default


class IntradayMarketSupervisor:
    """Orchestrates per-country intraday updates using helper modules.

    Responsibilities per loop iteration:
        1. Capture ticks every second into Redis.
        2. Maintain current 1m bar in Redis.
        3. Enqueue closed bars to Redis for later bulk flush.
    """

    def __init__(self, interval_seconds: int = 1, metrics_interval: int = 10, session_interval: int = 10, day_interval: int = 60, flush_interval: int = 60):
        self.interval_seconds = _env_int("THOR_TICK_INTERVAL_SEC", interval_seconds)
        self.metrics_interval = _env_int("THOR_METRIC_INTERVAL_SEC", metrics_interval)
        self.session_interval = _env_int("THOR_SESSIONVOL_INTERVAL_SEC", session_interval)
        self.day_interval = _env_int("THOR_24H_UPDATE_SEC", day_interval)
        self.flush_interval = _env_int("THOR_BAR_FLUSH_SEC", flush_interval)
        self.bar_flush_interval = self.flush_interval
        self.disabled = os.getenv("INTRADAY_SUPERVISOR_DISABLED", "").lower() in {"1", "true", "yes"}
        if self.disabled:
            logger.warning("IntradayMarketSupervisor disabled via INTRADAY_SUPERVISOR_DISABLED")
        self._workers = {}
        self._lock = threading.RLock()
        self._lag_alert_last = {}
        self._timers = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def on_market_open(self, market):
        import os
        scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
        if scheduler_mode == "heartbeat":
            logger.info("Heartbeat scheduler active; skipping legacy intraday worker for %s", self._get_normalized_country(market))
            return
        country = self._get_normalized_country(market)
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping worker start for %s", country)
            return
        if not self._tracking_enabled(market):
            logger.info(
                "Intraday metrics disabled for %s (is_active=%s, session_capture=%s)",
                country,
                getattr(market, "is_active", True),
                getattr(market, "enable_session_capture", True),
            )
            return
        with self._lock:
            if market.id in self._workers:
                logger.info("Intraday worker already active for %s", country)
                return
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"Intraday-{country}",
                args=(market, stop_event),
                daemon=True,
            )
            self._workers[market.id] = (thread, stop_event)
            thread.start()
            logger.info("Intraday metrics worker STARTED for %s", country)

    def on_market_close(self, market):
        import os
        scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
        if scheduler_mode == "heartbeat":
            logger.info("Heartbeat scheduler active; skipping legacy intraday close handler for %s", self._get_normalized_country(market))
            return
        country = self._get_normalized_country(market)
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping close handling for %s", country)
            return
        with self._lock:
            worker = self._workers.pop(market.id, None)
            if worker:
                thread, stop_event = worker
                stop_event.set()
                thread.join(timeout=5)
                logger.info("Intraday metrics worker STOPPED for %s", country)
            timers = self._timers.pop(market.id, None)
            if timers:
                for timer in timers.values():
                    timer.cancel()

        # Finalize metrics
        try:
            enriched, composite = get_enriched_quotes_with_composite()
        except Exception:
            logger.exception("Failed to fetch quotes for close metrics (%s)", country)
            return
        try:
            MarketCloseMetric.update_for_country_on_close(country, enriched)
        except Exception:
            logger.exception("MarketCloseMetric failed for %s", country)
        try:
            MarketRangeMetric.update_for_country_on_close(country)
        except Exception:
            logger.exception("MarketRangeMetric failed for %s", country)

        self._run_account_snapshot_once_per_day(country)

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------
    def _worker_loop(self, market, stop_event):
        country = self._get_normalized_country(market)
        if self.disabled:
            logger.info("Intraday worker requested for %s but supervisor is disabled", country)
            return
        logger.info("Intraday worker loop started for %s", country)

        while not stop_event.is_set():
            # Stop automatically if session tracking is turned off at runtime
            if not session_tracking_allowed(country):
                logger.info("Intraday worker stopping for %s: session tracking disabled", country)
                with self._lock:
                    self._workers.pop(market.id, None)
                    timers = self._timers.pop(market.id, None)
                if timers:
                    for timer in timers.values():
                        timer.cancel()
                return
            try:
                self._process_market_tick(market)
            except Exception:
                logger.exception("Intraday worker loop iteration failed for %s", country)

            stop_event.wait(self.interval_seconds)

        logger.info("Intraday worker loop EXITING for %s", country)

    def step_once(self):
        """Run a single intraday tick across all open markets (no internal loops)."""
        try:
            from GlobalMarkets.models.market import Market

            open_markets = Market.objects.filter(
                is_active=True,
                status='OPEN',
                enable_session_capture=True  # Only include markets with intraday tracking enabled
            )
        except Exception:
            logger.exception("Intraday step_once failed to load markets")
            return

        if not open_markets.exists():
            logger.debug("Intraday skipped: no open markets")
            return

        for market in open_markets:
            try:
                self._process_market_tick(market)
                self._maybe_alert_lag(self._get_normalized_country(market))
            except Exception:
                logger.exception("Intraday step_once failed for %s", self._get_normalized_country(market))

    # ------------------------------------------------------------------
    # Single tick processing (used by heartbeat job)
    # ------------------------------------------------------------------
    def _process_market_tick(self, market) -> None:
        country = self._get_normalized_country(market)

        if self.disabled:
            logger.info("Intraday metrics disabled; skipping tick for %s", country)
            return

        if not session_tracking_allowed(country):
            logger.info("Intraday tick skipped; session tracking disabled for %s", country)
            return

        enriched, _ = get_enriched_quotes_with_composite()
        quote_count = len(enriched) if enriched else 0
        if quote_count == 0:
            logger.debug("Intraday %s: no quotes returned; skipping tick capture", country)

        closed_count = 0
        updated_count = 0
        filtered_rows = []

        for row in enriched or []:
            row_country = normalize_country_code(
                row.get('country') or row.get('instrument', {}).get('country')
            )
            if row_country and row_country != country:
                continue
            sym = row.get('instrument', {}).get('symbol')
            if not sym:
                continue
            sym = sym.lstrip('/').upper()
            filtered_rows.append(row)
            tick = {
                "symbol": sym,
                "country": country,
                "price": row.get('last'),
                "volume": row.get('volume'),
                "bid": row.get('bid'),
                "ask": row.get('ask'),
                "timestamp": row.get('timestamp'),
            }
            try:
                live_data_redis.set_tick(country, sym, tick, ttl=10)
                closed_bar, current_bar = live_data_redis.upsert_current_bar_1m(country, sym, tick)
                updated_count += 1
                if closed_bar:
                    live_data_redis.enqueue_closed_bar(country, closed_bar)
                    closed_count += 1
            except Exception:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception("Intraday %s: tick capture failed for %s", country, sym)
                else:
                    logger.warning("Intraday %s: tick capture failed for %s", country, sym)

        if filtered_rows:
            try:
                update_session_volume_for_country(country, filtered_rows)
            except Exception:
                logger.exception("Intraday %s: session volume update failed", country)

    def _flush_closed_bars_1m(self, country: str):
        # Single bar writer: Redis → services.intraday.flush only. No per-tick DB writes elsewhere.
        total = 0
        batch_size = 500
        try:
            while True:
                inserted = flush_closed_bars(country, batch_size=batch_size)
                if not inserted:
                    break
                total += inserted
        except Exception:
            logger.exception("Intraday %s: flush_1m failed", country)
            return
        if total:
            logger.info("Intraday flush 1m bars: country=%s inserted=%s", country, total)

    def _tracking_enabled(self, market) -> bool:
           return session_tracking_allowed(market)

    def _refresh_and_check_tracking(self, market) -> bool:
        """Refresh market flags and determine if intraday tracking should continue."""
        try:
            market.refresh_from_db(fields=["is_active", "enable_session_capture"])
        except Exception:
            logger.info("Market %s no longer exists; stopping intraday worker", self._get_normalized_country(market))
            return False
        return self._tracking_enabled(market)

    def _get_normalized_country(self, market) -> str:
        raw = getattr(market, "country", None)
        normalized = normalize_country_code(raw)
        if normalized:
            return normalized
        if raw:
            return raw.strip() or "?"
        return "?"

    def _run_account_snapshot_once_per_day(self, country: str):
        if country != "USA":
            logger.debug("Account snapshot trigger skipped for %s close (USA only)", country)
            return

        trading_date = timezone.localdate()
        lock_key = self._acquire_snapshot_lock(trading_date)
        if not lock_key:
            logger.debug("Account snapshot already triggered for %s", trading_date)
            return

        try:
            succeeded = trigger_daily_account_snapshots(
                trading_date=trading_date,
                broker="SCHWAB",
                source="AUTO",
                overwrite=False,
            )
        except Exception:
            self._release_snapshot_lock(lock_key)
            logger.exception("Account snapshot trigger crashed for %s", trading_date)
            return

        if succeeded:
            logger.info("Account daily snapshots captured for %s", trading_date)
        else:
            self._release_snapshot_lock(lock_key)
            logger.error("Account daily snapshots failed for %s", trading_date)

    def _acquire_snapshot_lock(self, trading_date) -> Optional[str]:
        key = f"{SNAPSHOT_LOCK_PREFIX}{trading_date.isoformat()}"
        try:
            acquired = live_data_redis.client.set(key, "1", nx=True, ex=SNAPSHOT_LOCK_TTL_SECONDS)
        except Exception:
            logger.exception("Failed to acquire account snapshot lock for %s", trading_date)
            return None
        return key if acquired else None

    def _release_snapshot_lock(self, key: str) -> None:
        try:
            live_data_redis.client.delete(key)
        except Exception:
            logger.exception("Failed to release account snapshot lock %s", key)

    def _maybe_alert_lag(self, country: str, *, threshold_minutes: int = 3, cooldown_minutes: int = 5) -> None:
        """Log a warning if a country's intraday bars are stale beyond threshold.

        Uses a cooldown to avoid log spam.
        """
        now = timezone.now()
        try:
            last_ts = (
                MarketIntraday.objects
                .filter(country=country)
                .order_by('-timestamp_minute')
                .values_list('timestamp_minute', flat=True)
                .first()
            )
        except Exception:
            logger.exception("Lag check failed for %s", country)
            return

        if last_ts is None:
            # Only emit once per cooldown
            last_alert = self._lag_alert_last.get(country)
            if not last_alert or (now - last_alert) >= timedelta(minutes=cooldown_minutes):
                logger.warning("Intraday %s: no bars exist yet (lag check)", country)
                self._lag_alert_last[country] = now
            return

        lag = now - last_ts
        if lag <= timedelta(minutes=threshold_minutes):
            return

        last_alert = self._lag_alert_last.get(country)
        if last_alert and (now - last_alert) < timedelta(minutes=cooldown_minutes):
            return

        logger.warning(
            "Intraday %s lagging: last bar %s (%.1f min ago)",
            country,
            last_ts,
            lag.total_seconds() / 60.0,
        )
        self._lag_alert_last[country] = now


# Global singleton
intraday_market_supervisor = IntradayMarketSupervisor()

