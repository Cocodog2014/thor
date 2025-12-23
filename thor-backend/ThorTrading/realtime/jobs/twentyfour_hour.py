"""Heartbeat job wrapper for 24-hour rolling stats."""
import logging

from ThorTrading.services.twentyfour_hour_job import TwentyFourHourJob

log = logging.getLogger(__name__)


def register(registry):
    job = TwentyFourHourJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
