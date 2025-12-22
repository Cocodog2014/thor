"""Job registry plugin loader for realtime heartbeat.

Keeps realtime generic by loading job providers from settings.REALTIME_JOB_PROVIDERS.
"""
from __future__ import annotations

import importlib
import logging
from typing import List

from django.conf import settings

from core.infra.jobs import JobRegistry

logger = logging.getLogger(__name__)


def register_jobs(registry: JobRegistry) -> List[str]:
    """Load job providers defined in settings and register their jobs."""

    providers = getattr(settings, "REALTIME_JOB_PROVIDERS", []) or []
    job_names: List[str] = []

    for dotted_path in providers:
        try:
            module = importlib.import_module(dotted_path)
            register_fn = getattr(module, "register", None)
            if callable(register_fn):
                added = register_fn(registry) or []
                job_names.extend(added)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register jobs from provider %s", dotted_path)

    logger.info("Registered realtime jobs: %s", job_names)
    return job_names


__all__ = ["register_jobs"]
