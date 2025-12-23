"""Heartbeat job wrapper for intraday ticks."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.intraday_supervisor.supervisor import intraday_market_supervisor

log = logging.getLogger(__name__)


class IntradayJob(Job):
    name = "intraday_tick"

    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        intraday_market_supervisor.step_once()


def register(registry):
    job = IntradayJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
