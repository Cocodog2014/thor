"""Heartbeat job wrapper for VWAP minute capture."""
import logging

from ThorTrading.services.vwap_minute_capture_job import VwapMinuteCaptureJob

log = logging.getLogger(__name__)


def register(registry):
    job = VwapMinuteCaptureJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
