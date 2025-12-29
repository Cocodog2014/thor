"""GlobalMarkets realtime job provider for the heartbeat registry.

Jobs registered here are passive definitions only:
- Status job: reconciles and persists Market.status in the DB.
- Broadcast job: pushes market clocks/status snapshots to WebSockets.
- Cache job: stores latest status snapshots for quick access.
- Active session job: publishes the routing key (session:<n>) used by ThorTrading streaming/flush.
Nothing runs until the heartbeat engine starts and ticks these jobs.
"""
import logging

from GlobalMarkets.jobs.active_session import PublishActiveSessionJob
from GlobalMarkets.jobs.broadcast import BroadcastMarketClocksJob
from GlobalMarkets.jobs.status_cache import CacheMarketStatusJob
from GlobalMarkets.jobs.status import ReconcileMarketStatusesJob

logger = logging.getLogger(__name__)


def register(registry):
    job_names = []

    try:
        status_job = ReconcileMarketStatusesJob()
        registry.register(status_job, interval_seconds=1)
        job_names.append(status_job.name)

        broadcast_job = BroadcastMarketClocksJob()
        registry.register(broadcast_job, interval_seconds=1)
        job_names.append(broadcast_job.name)

        status_cache_job = CacheMarketStatusJob()
        registry.register(status_cache_job, interval_seconds=2)
        job_names.append(status_cache_job.name)

        active_session_job = PublishActiveSessionJob()
        registry.register(active_session_job, interval_seconds=2)
        job_names.append(active_session_job.name)

        logger.info("GlobalMarkets jobs registered: %s", job_names)
    except Exception:
        logger.exception("GlobalMarkets provider failed to register jobs")

    return job_names
