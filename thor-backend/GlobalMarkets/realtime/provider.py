"""GlobalMarkets realtime job provider for the heartbeat registry.

Jobs registered here are passive definitions only:
- Status job: reconciles and persists Market.status in the DB.
- Broadcast job: pushes market clocks/status snapshots to WebSockets.
Nothing runs until the heartbeat engine starts and ticks these jobs.
"""
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
