"""Heartbeat job wrapper for 52-week extremes tracking."""
import logging

from ThorTrading.services.week52_extremes_job import Week52ExtremesJob

log = logging.getLogger(__name__)


def register(registry):
    job = Week52ExtremesJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
