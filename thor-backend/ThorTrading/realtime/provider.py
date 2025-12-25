from __future__ import annotations
"""ThorTrading realtime job provider for the single heartbeat scheduler.

Registers all ThorTrading heartbeat jobs explicitly so the only timer in use is
the core heartbeat loop in thor_project/realtime/engine.py.
"""
import logging

from ThorTrading.realtime.jobs import (
    intraday_tick,
    closed_bars_flush,
    market_metrics,
    market_grader,
    week52_extremes,
    vwap_minute_capture,
    twentyfour_hour,
    preopen_backtest,
)

logger = logging.getLogger(__name__)


_JOB_MODULES = (
    intraday_tick,
    closed_bars_flush,
    market_metrics,
    market_grader,
    week52_extremes,
    vwap_minute_capture,
    twentyfour_hour,
    preopen_backtest,
)


def register(registry):
    job_names = []

    for module in _JOB_MODULES:
        try:
            added = module.register(registry) or []
            job_names.extend(added)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register job module %s", getattr(module, "__name__", module))

    logger.info("ThorTrading jobs registered: %s", job_names)
    return job_names


__all__ = ["register"]
