"""Compatibility wrapper for job registration.

Delegates to thor_project.realtime.registry so callers relying on the old
register_all_jobs() entrypoint keep working after the job provider cleanup.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.jobs import JobRegistry

logger = logging.getLogger(__name__)


def register_all_jobs(registry: JobRegistry) -> int:
    """Register jobs using the configured realtime providers.

    Args:
        registry: JobRegistry instance to populate.

    Returns:
        Number of jobs registered by this call.
    """
    from thor_project.realtime.registry import register_jobs as _register_jobs

    before = len(registry.jobs)
    job_names = _register_jobs(registry) or []
    count = len(registry.jobs) - before
    logger.info("Registered %d jobs via realtime providers: %s", count, job_names)
    return count


__all__ = ["register_all_jobs"]
