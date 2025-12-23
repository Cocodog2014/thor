"""ThorTrading realtime job provider for the single heartbeat scheduler.

Registers all ThorTrading heartbeat jobs explicitly so the only timer in use is
the core heartbeat loop in thor_project/realtime/engine.py.
"""
import logging

from ThorTrading.services.intraday_job import IntradayJob
from ThorTrading.services.week52_extremes_job import Week52ExtremesJob
from ThorTrading.services.market_metrics_job import MarketMetricsJob
from ThorTrading.services.twentyfour_hour_job import TwentyFourHourJob
from ThorTrading.services.preopen_backtest_job import PreOpenBacktestJob
from ThorTrading.services.vwap_minute_capture_job import VwapMinuteCaptureJob
from ThorTrading.services.closed_bars_flush_job import ClosedBarsFlushJob

logger = logging.getLogger(__name__)


def register(registry):
    job_names = []

    jobs = [
        IntradayJob(interval_seconds=1.0),
        Week52ExtremesJob(interval_seconds=2.0),
        MarketMetricsJob(interval_seconds=10.0),
        TwentyFourHourJob(interval_seconds=30.0),
        PreOpenBacktestJob(interval_seconds=30.0),
        VwapMinuteCaptureJob(interval_seconds=60.0),
        ClosedBarsFlushJob(interval_seconds=60.0),
    ]

    for job in jobs:
        registry.register(job, interval_seconds=job.interval_seconds)
        job_names.append(job.name)

    logger.info("ThorTrading jobs registered: %s", job_names)
    return job_names


__all__ = ["register"]
