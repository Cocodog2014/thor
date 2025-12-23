"""Heartbeat job wrapper for market metrics updates."""
import logging

from ThorTrading.services.market_metrics_job import MarketMetricsJob

log = logging.getLogger(__name__)


def register(registry):
    job = MarketMetricsJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
