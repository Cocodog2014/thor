"""Heartbeat job wrapper for flushing closed bars."""
import logging

from ThorTrading.services.closed_bars_flush_job import ClosedBarsFlushJob

log = logging.getLogger(__name__)


def register(registry):
    job = ClosedBarsFlushJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
