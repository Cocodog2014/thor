"""Heartbeat job for market grading.

Runs the MarketGrader single-pass grading under the unified scheduler.
"""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.api.views.market_grader import _grade_pending_once

logger = logging.getLogger(__name__)


class MarketGraderJob(Job):
    name = "market_grader"

    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            _grade_pending_once()
        except Exception:
            logger.exception("market_grader: grading pass failed")


__all__ = ["MarketGraderJob"]
