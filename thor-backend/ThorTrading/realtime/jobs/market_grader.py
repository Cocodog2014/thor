"""Heartbeat job wrapper for market grading."""
import logging

from ThorTrading.services.market_grader_job import MarketGraderJob

log = logging.getLogger(__name__)


def register(registry):
    job = MarketGraderJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
