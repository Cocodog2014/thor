# FutureTrading/services/IntradayMarketSupervisor.py

"""
Intraday Market Supervisor

Runs all intraday metrics while a market is OPEN:
    - MarketHighMetric.update_from_quotes(...)
    - MarketLowMetric.update_from_quotes(...)

Runs closing metrics when a market transitions to CLOSED:
    - MarketCloseMetric.update_for_country_on_close(...)
    - MarketRangeMetric.update_for_country_on_close(...)

This supervisor is started/stopped by the global MarketMonitor.
"""

import logging
import threading
import time
import os
import json
from django.utils import timezone
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.constants import FUTURES_SYMBOLS
from FutureTrading.services.vwap import vwap_service

from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.market_metrics import (
    MarketHighMetric,
    MarketLowMetric,
    MarketCloseMetric,
    MarketRangeMetric,
)

logger = logging.getLogger(__name__)


class IntradayMarketSupervisor:
    """
    Manages background metric updates for each open market (country).

    Features:
        - Each OPEN market gets its own worker thread.
        - High/Low metrics update on a repeating schedule.
        - When the market closes, the worker stops and close/range metrics run once.
    """

    def __init__(self, interval_seconds: int = 10):
        # How often to refresh highs/lows while market is open
        self.interval_seconds = interval_seconds

        # Allow migrations/maintenance to disable the background workers entirely
        self.disabled = os.getenv("INTRADAY_SUPERVISOR_DISABLED", "").lower() in {"1", "true", "yes"}
        if self.disabled:
            logger.warning("IntradayMarketSupervisor disabled via INTRADAY_SUPERVISOR_DISABLED")

        # Map: market.id -> (thread, stop_event)
        self._workers = {}
        self._lock = threading.RLock()

    # --------------------------------------------------------------------
    # PUBLIC API - Called by MarketMonitor
    # --------------------------------------------------------------------

    def on_market_open(self, market):
        """Start intraday metric updates for this market (if not already running)."""
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping worker start for %s", market.country)
            return
        with self._lock:
            if market.id in self._workers:
                logger.info("Intraday worker already active for %s", market.country)
                return

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"Intraday-{market.country}",
                args=(market, stop_event),
                daemon=True,
            )

            # Register worker for this market
            self._workers[market.id] = (thread, stop_event)
            thread.start()

            logger.info("Intraday metrics worker STARTED for %s", market.country)

    def on_market_close(self, market):
        """Stop intraday updates and finalize market_close & market_range metrics."""
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping close handling for %s", market.country)
            return
        with self._lock:
            worker = self._workers.pop(market.id, None)
            if worker:
                thread, stop_event = worker
                stop_event.set()
                thread.join(timeout=5)
                logger.info("Intraday metrics worker STOPPED for %s", market.country)

        # Now run close + range metrics once
        try:
            enriched, composite = get_enriched_quotes_with_composite()
        except Exception:
            logger.exception(
                "Failed to fetch quotes for close metrics (%s)", market.country
            )
            return

        try:
            MarketCloseMetric.update_for_country_on_close(market.country, enriched)
        except Exception:
            logger.exception("MarketCloseMetric failed for %s", market.country)

        try:
            MarketRangeMetric.update_for_country_on_close(market.country)
        except Exception:
            logger.exception("MarketRangeMetric failed for %s", market.country)

    # --------------------------------------------------------------------
    # INTERNAL WORKER LOOP
    # --------------------------------------------------------------------

    def _worker_loop(self, market, stop_event: threading.Event):
        """
        Loop that runs while market is OPEN.
        Updates intraday metrics repeatedly until closed.
        """
        if self.disabled:
            logger.info("Intraday worker requested for %s but supervisor is disabled", market.country)
            return
        country = market.country
        logger.info("Intraday worker loop started for %s", country)

        while not stop_event.is_set():
            try:
                enriched, composite = get_enriched_quotes_with_composite()

                # Continuous intraday updates
                MarketHighMetric.update_from_quotes(country, enriched)
                MarketLowMetric.update_from_quotes(country, enriched)

                # Rolling VWAP precomputation
                window_minutes = int(os.getenv('ROLLING_VWAP_WINDOW_MINUTES', '30'))
                now_dt = timezone.now().replace(second=0, microsecond=0)
                vwap_payload = {}
                for sym in FUTURES_SYMBOLS:
                    try:
                        val = vwap_service.calculate_rolling_vwap(sym, window_minutes, now_dt=now_dt)
                        vwap_payload[sym] = str(val) if val is not None else None
                    except Exception as vw_err:
                        logger.debug("Rolling VWAP calc failed for %s: %s", sym, vw_err)
                        vwap_payload[sym] = None
                live_data_redis.set(
                    f"rolling_vwap:{window_minutes}",
                    json.dumps({
                        'window_minutes': window_minutes,
                        'as_of': now_dt.isoformat(),
                        'values': vwap_payload,
                    }),
                    ex=120,
                )

            except Exception:
                logger.exception("Intraday metrics update failed for %s", country)

            stop_event.wait(self.interval_seconds)

        logger.info("Intraday worker loop EXITING for %s", country)


# Global singleton used by MarketMonitor
intraday_market_supervisor = IntradayMarketSupervisor()
