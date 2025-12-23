"""Heartbeat job wrapper for intraday ticks."""
import logging

from ThorTrading.services.intraday_job import IntradayJob

log = logging.getLogger(__name__)


def register(registry):
    job = IntradayJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
