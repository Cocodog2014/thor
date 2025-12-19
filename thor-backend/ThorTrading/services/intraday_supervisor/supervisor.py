import logging
import os
import threading
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.account_snapshots import trigger_account_daily_snapshots
from ThorTrading.services.country_codes import normalize_country_code
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


SNAPSHOT_LOCK_PREFIX = "thor:account_snapshot_eod:"
SNAPSHOT_LOCK_TTL_SECONDS = 60 * 60 * 48  # 48h safety window


class IntradayMarketSupervisor:
    """Orchestrates per-country intraday updates using helper modules.

    Responsibilities per loop iteration:
        1. Capture ticks every second into Redis.
        2. Maintain current 1m bar in Redis.
        3. Enqueue closed bars to Redis for later bulk flush.
    """

    def __init__(self, interval_seconds: int = 1, metrics_interval: int = 10, session_interval: int = 10, day_interval: int = 60):
        self.interval_seconds = interval_seconds
        self.metrics_interval = metrics_interval
        self.session_interval = session_interval
        self.day_interval = day_interval
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
        country = self._get_normalized_country(market)
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping worker start for %s", country)
            return
        if not self._tracking_enabled(market):
            logger.info(
                "Intraday metrics disabled for %s (is_active=%s, enable_futures_capture=%s)",
                country,
                getattr(market, "is_active", True),
                getattr(market, "enable_futures_capture", True),
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

        # Schedule slower tasks (metrics/session/24h) on their own timers
        def _schedule_timer(name, interval, func):
            timers_for_market = self._timers.setdefault(market.id, {})

            def _run():
                if stop_event.is_set():
                    return
                try:
                    func()
                except Exception:
                    logger.exception("Intraday %s %s task failed", country, name)
                finally:
                    if not stop_event.is_set():
                        t = threading.Timer(interval, _run)
                        t.daemon = True
                        timers_for_market[name] = t
                        t.start()

            t = threading.Timer(interval, _run)
            t.daemon = True
            timers_for_market[name] = t
            t.start()

        # Placeholder slow tasks (no-ops for now; hook real logic later)
        _schedule_timer("metrics", self.metrics_interval, lambda: None)
        _schedule_timer("session", self.session_interval, lambda: None)
        _schedule_timer("day", self.day_interval, lambda: None)

        while not stop_event.is_set():
            try:
                if not self._refresh_and_check_tracking(market):
                    logger.info(
                        "Intraday worker stopping for %s (market disabled)",
                        country,
                    )
                    break

                enriched, _ = get_enriched_quotes_with_composite()
                quote_count = len(enriched) if enriched else 0
                if quote_count == 0:
                    logger.debug("Intraday %s: no quotes returned; skipping tick capture", country)

                closed_count = 0
                updated_count = 0

                for row in enriched or []:
                    sym = row.get('instrument', {}).get('symbol')
                    if not sym:
                        continue
                    sym = sym.lstrip('/').upper()
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
                        logger.exception("Intraday %s: tick capture failed for %s", country, sym)

                logger.info(
                    "Intraday %s → ticks=%s, closed_1m=%s",
                    country,
                    updated_count,
                    closed_count,
                )
            except Exception:
                logger.exception("Intraday metrics update failed for %s", country)

            stop_event.wait(self.interval_seconds)

        logger.info("Intraday worker loop EXITING for %s", country)

    def _tracking_enabled(self, market) -> bool:
        return getattr(market, "is_active", True) and getattr(market, "enable_futures_capture", True)

    def _refresh_and_check_tracking(self, market) -> bool:
        """Refresh market flags and determine if intraday tracking should continue."""
        try:
            market.refresh_from_db(fields=["is_active", "enable_futures_capture"])
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
            succeeded = trigger_account_daily_snapshots(
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

