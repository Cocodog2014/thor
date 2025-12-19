"""Heartbeat-friendly intraday job wrapper.

Transforms the intraday supervisor into a single-step job the heartbeat can run
on an interval.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.intraday_supervisor.supervisor import intraday_market_supervisor


class IntradayJob(Job):
    name = "intraday_tick"

    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        intraday_market_supervisor.step_once()
