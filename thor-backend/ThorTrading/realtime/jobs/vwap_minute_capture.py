"""Heartbeat job wrapper for VWAP minute capture."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.indicators.vwap_minute import capture_vwap_minute

log = logging.getLogger(__name__)


class VwapMinuteCaptureJob(Job):
    """Capture VWAP minute snapshots from latest quotes."""

    name = "vwap_minute_capture"

    def __init__(self, interval_seconds: float = 60.0):
        self.interval_seconds = max(5.0, float(interval_seconds))

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        samples, rows_created = capture_vwap_minute(ctx.shared_state)
        if samples or rows_created:
            log.debug("VWAP capture: samples=%s rows=%s", samples, rows_created)


def register(registry):
    job = VwapMinuteCaptureJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
