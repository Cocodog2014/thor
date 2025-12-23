"""Single location for job registration.

All jobs are imported and registered here. The heartbeat command and
AppConfig both call register_all_jobs() to populate the registry.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.jobs import JobRegistry

logger = logging.getLogger(__name__)


def register_all_jobs(registry: JobRegistry) -> int:
    """Register all jobs with the provided registry.
    
    Args:
        registry: JobRegistry instance to populate.
        
    Returns:
        Number of jobs registered.
    """
    # Import all job classes (lazy to avoid circular imports)
    from ThorTrading.realtime.jobs.intraday_tick import IntradayJob
    from ThorTrading.services.twentyfour_hour_job import TwentyFourHourJob
    from ThorTrading.realtime.jobs.market_metrics import MarketMetricsJob
    from ThorTrading.realtime.jobs.closed_bars_flush import ClosedBarsFlushJob
    from ThorTrading.services.week52_extremes_job import Week52ExtremesJob
    from ThorTrading.services.preopen_backtest_job import PreOpenBacktestJob
    from ThorTrading.realtime.jobs.market_grader import MarketGraderJob

    # Register all jobs with their intervals (in execution order for clarity)
    registry.register(IntradayJob(interval_seconds=1.0))
    registry.register(Week52ExtremesJob(interval_seconds=2.0))
    registry.register(MarketGraderJob(interval_seconds=1.0))
    registry.register(MarketMetricsJob(interval_seconds=10.0))
    registry.register(TwentyFourHourJob(interval_seconds=30.0))
    registry.register(PreOpenBacktestJob(interval_seconds=30.0))
    registry.register(ClosedBarsFlushJob(interval_seconds=60.0))

    count = len(registry.jobs)
    logger.info("Registered %d jobs", count)
    return count


__all__ = ["register_all_jobs"]
