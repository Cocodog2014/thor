"""Heartbeat job wrapper for pre-open backtests."""
import logging

from ThorTrading.services.preopen_backtest_job import PreOpenBacktestJob

log = logging.getLogger(__name__)


def register(registry):
    job = PreOpenBacktestJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
