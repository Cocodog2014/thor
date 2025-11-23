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

        # Map: market.id -> (thread, stop_event)
        self._workers = {}
        self._lock = threading.RLock()

    # --------------------------------------------------------------------
    # PUBLIC API - Called by MarketMonitor
    # --------------------------------------------------------------------

    def on_market_open(self, market):
        """Start intraday metric updates for this market (if not already running)."""
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
        country = market.country
        logger.info("Intraday worker loop started for %s", country)

        while not stop_event.is_set():
            try:
                enriched, composite = get_enriched_quotes_with_composite()

                # Continuous intraday updates
                MarketHighMetric.update_from_quotes(country, enriched)
                MarketLowMetric.update_from_quotes(country, enriched)

            except Exception:
                logger.exception("Intraday metrics update failed for %s", country)

            stop_event.wait(self.interval_seconds)

        logger.info("Intraday worker loop EXITING for %s", country)


# Global singleton used by MarketMonitor
intraday_market_supervisor = IntradayMarketSupervisor()
