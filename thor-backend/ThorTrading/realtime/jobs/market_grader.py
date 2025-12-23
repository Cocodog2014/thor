"""Heartbeat job wrapper for market grading."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.sessions.grading import grade_pending_once

log = logging.getLogger(__name__)


class MarketGraderJob(Job):
    name = "market_grader"

    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            grade_pending_once()
        except Exception:
            log.exception("market_grader: grading pass failed")


def register(registry):
    job = MarketGraderJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
