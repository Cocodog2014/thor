"""Job registry helpers for realtime heartbeat."""
from __future__ import annotations

import logging
from typing import List

from core.infra.jobs import JobRegistry

logger = logging.getLogger(__name__)


def register_jobs(registry: JobRegistry) -> List[str]:
    """Register jobs into the provided registry.

    Currently empty (GlobalMarkets-first mode); returns the list of registered job names.
    """
    _ = registry  # Placeholder to show intent and avoid lint noise
    return []


__all__ = ["register_jobs"]
