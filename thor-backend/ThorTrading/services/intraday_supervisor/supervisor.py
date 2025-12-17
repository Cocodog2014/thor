import logging
import threading
import os
from typing import Optional

from django.utils import timezone
from django.db import transaction

from ThorTrading.constants import FUTURES_SYMBOLS
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.market_metrics import (
    MarketHighMetric,
    MarketLowMetric,
    MarketCloseMetric,
    MarketRangeMetric,
)
from ThorTrading.services.account_snapshots import trigger_account_daily_snapshots
from ThorTrading.services.country_codes import normalize_country_code
from LiveData.shared.redis_client import live_data_redis

from .feed_24h import update_24h_for_country
from .intraday_bars import update_intraday_bars_for_country
from .session_volume import update_session_volume_for_country
from .vwap_precompute import precompute_rolling_vwap

logger = logging.getLogger(__name__)


SNAPSHOT_LOCK_PREFIX = "thor:account_snapshot_eod:"
SNAPSHOT_LOCK_TTL_SECONDS = 60 * 60 * 48  # 48h safety window


class IntradayMarketSupervisor:
    """Orchestrates per-country intraday updates using helper modules.

    Responsibilities per loop iteration:
        1. Update intraday session highs/lows via metrics.
        2. Upsert & update rolling 24h stats (extremes, range, volume).
        3. Create/get current minute OHLCV bars.
        4. Accumulate session volume on MarketSession.
        5. Precompute rolling VWAP snapshot.
    """

    def __init__(self, interval_seconds: int = 1):
        self.interval_seconds = interval_seconds
        self.disabled = os.getenv("INTRADAY_SUPERVISOR_DISABLED", "").lower() in {"1", "true", "yes"}
        if self.disabled:
            logger.warning("IntradayMarketSupervisor disabled via INTRADAY_SUPERVISOR_DISABLED")
        self._workers = {}
        self._lock = threading.RLock()

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
            try:
                if not self._refresh_and_check_tracking(market):
                    logger.info(
                        "Intraday worker stopping for %s (market disabled)",
                        country,
                    )
                    break

                enriched, composite = get_enriched_quotes_with_composite()

                # 1) High/Low metrics
                MarketHighMetric.update_from_quotes(country, enriched)
                MarketLowMetric.update_from_quotes(country, enriched)

                # 2) 24h stats
                twentyfour_counts, twentyfour_map = update_24h_for_country(country, enriched)

                # 3) 1m bars (needs twentyfour_map)
                intraday_counts = update_intraday_bars_for_country(country, enriched, twentyfour_map)

                # 4) session volume
                session_counts = update_session_volume_for_country(country, enriched)

                # 5) VWAP precompute
                precompute_rolling_vwap(FUTURES_SYMBOLS)

                logger.info(
                    "Intraday %s → 24h=%s, intraday=%s, session_vol=%s",
                    country,
                    twentyfour_counts,
                    intraday_counts,
                    session_counts,
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


# Global singleton
intraday_market_supervisor = IntradayMarketSupervisor()

