# ThorTrading/services/PreOpenBacktestSupervisor.py

"""
Pre-Open Backtest Supervisor

Watches GlobalMarkets control markets and, when a market is within
T-minus 60 seconds of OPEN, runs backtest statistics for all futures.

This does NOT create MarketSession rows; it simply ensures that the
backtest stats are computed right before the open, so:
  - logs show pre-open snapshots
  - the same compute function is "warmed up" ahead of MarketOpenCapture

MarketOpenCapture still copies the stats into the MarketSession row
(see Step 2 wiring in MarketOpenCaptureService).
"""

from __future__ import annotations

import logging
import threading
import time
import os
from typing import Optional

from django.conf import settings
from django.utils import timezone

from ThorTrading.constants import FUTURES_SYMBOLS
from ThorTrading.services.backtest_stats import (
    compute_backtest_stats_for_country_future,
)

logger = logging.getLogger(__name__)


class _PreOpenBacktestSupervisor:
    """Background thread that runs backtests ~1 minute before market open."""

    def __init__(self, interval_seconds: float = 30.0):
        # how often we check markets / countdown
        self._interval = max(5.0, float(interval_seconds))
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._tick = 0

    def start(self):
        import os
        if os.getenv("HEARTBEAT_ENABLED", "").lower() in {"1", "true", "yes"}:
            logger.info("Heartbeat scheduler active; skipping legacy pre-open backtest supervisor")
            return
        with self._lock:
            if self._running:
                logger.debug("Pre-open backtest supervisor already running; skip start")
                return
            self._running = True
            t = threading.Thread(
                target=self._run,
                name="PreOpenBacktestSupervisor",
                daemon=True,
            )
            self._thread = t
            t.start()
            logger.info(
                "📊 Pre-open backtest supervisor started (interval=%.1fs)",
                self._interval,
            )

    def stop(self):
        with self._lock:
            self._running = False
        logger.info("🛑 Pre-open backtest supervisor stop requested")

    def _run(self):
        # Lazy import to avoid app loading issues
        from GlobalMarkets.models.market import Market

        while True:
            with self._lock:
                if not self._running:
                    break

            try:
                markets = Market.objects.filter(is_active=True, is_control_market=True)

                for m in markets:
                    status = m.get_market_status()
                    if not status:
                        continue

                    # We only care about the next OPEN event
                    if status.get("next_event") != "open":
                        continue

                    seconds = int(status.get("seconds_to_next_event", 0) or 0)

                    # Only fire when we are in the [1, 60] second pre-open window
                    if seconds <= 0 or seconds > 60:
                        continue

                    # At this point, market m is about to OPEN within a minute
                    logger.info(
                        "⏳ Pre-open window for %s: %ss to open – running backtests",
                        m.country,
                        seconds,
                    )

                    for sym in FUTURES_SYMBOLS + ["TOTAL"]:
                        try:
                            stats = compute_backtest_stats_for_country_future(
                                country=m.country,
                                future=sym,
                                as_of=timezone.now(),
                            )
                            # For now we simply log. The actual copy into the DB row
                            # occurs in MarketOpenCapture via data.update(stats).
                            logger.debug(
                                "[pre-open] %s / %s backtest snapshot: %s",
                                m.country,
                                sym,
                                stats,
                            )
                        except Exception:
                            logger.exception(
                                "[pre-open] Backtest stats failed for %s / %s",
                                m.country,
                                sym,
                            )

            except Exception:
                logger.exception("Pre-open backtest supervisor iteration failed")

            time.sleep(self._interval)

            # Optional heartbeat log
            self._tick += 1
            if self._tick % int(max(1, 60 / self._interval)) == 0:
                logger.info(
                    "💓 [pre-open backtest heartbeat] interval=%.1fs",
                    self._interval,
                )


# -------------------------
# Singleton + public API
# -------------------------

__supervisor_instance: _PreOpenBacktestSupervisor | None = None


def _get_interval() -> float:
    setting = getattr(settings, "FUTURETRADING_PREOPEN_BACKTEST_INTERVAL", None)
    if setting is not None:
        return float(setting)
    env = os.getenv("FUTURETRADING_PREOPEN_BACKTEST_INTERVAL")
    return float(env) if env else 30.0


def get_preopen_backtest_supervisor() -> _PreOpenBacktestSupervisor:
    global __supervisor_instance
    if __supervisor_instance is None:
        __supervisor_instance = _PreOpenBacktestSupervisor(
            interval_seconds=_get_interval()
        )
    return __supervisor_instance


def _is_enabled() -> bool:
    setting = getattr(settings, "FUTURETRADING_ENABLE_PREOPEN_BACKTEST", None)
    if setting is not None:
        return bool(setting)
    env = os.getenv("FUTURETRADING_ENABLE_PREOPEN_BACKTEST")
    if env is None:
        return True
    return env.strip().lower() not in {"0", "false", "no", "off"}


def start_preopen_backtest_supervisor() -> None:
    """
    Start the pre-open backtest supervisor.

    This is safe to call from AppConfig.ready(); it guards against
    duplicate threads and can be disabled via settings/env.
    """
    # Avoid duplicates under autoreloader by scanning thread names
    for t in threading.enumerate():
        if t.name == "PreOpenBacktestSupervisor":
            logger.debug(
                "Duplicate PreOpenBacktestSupervisor thread detected; skipping start"
            )
            return

    if not _is_enabled():
        logger.info(
            "⚠️ Pre-open backtest supervisor disabled by settings/env; not starting"
        )
        return

    sup = get_preopen_backtest_supervisor()
    sup.start()


def stop_preopen_backtest_supervisor() -> None:
    sup = get_preopen_backtest_supervisor()
    sup.stop()

