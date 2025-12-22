"""GlobalMarkets realtime job provider for the heartbeat registry."""
import logging

from GlobalMarkets.jobs.status import ReconcileMarketStatusesJob
from GlobalMarkets.jobs.broadcast import BroadcastMarketClocksJob

logger = logging.getLogger(__name__)


def register(registry):
    job_names = []

    status_job = ReconcileMarketStatusesJob()
    registry.register(status_job, interval_seconds=1)
    job_names.append(status_job.name)

    broadcast_job = BroadcastMarketClocksJob()
    registry.register(broadcast_job, interval_seconds=1)
    job_names.append(broadcast_job.name)

    return job_names
