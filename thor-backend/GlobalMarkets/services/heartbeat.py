"""Infrastructure heartbeat loop.

Single timer that dispatches registered jobs. Keep this file free of
domain-specific imports or logic.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable, Protocol


class Job(Protocol):
    """Lightweight job interface consumed by the heartbeat."""

    name: str

    def run(self, ctx: "HeartbeatContext") -> None:
        ...

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        ...


@dataclass
class JobMeta:
    job: Job
    interval_seconds: float | None = None
    last_run: float | None = None


@dataclass
class HeartbeatContext:
    logger: logging.Logger
    shared_state: dict[str, Any]
    settings: Any | None = None
    stop_event: threading.Event | None = None


class JobRegistry:
    """Maintains jobs and executes any that are due on the current tick."""

    def __init__(self, jobs: Iterable[JobMeta] | None = None) -> None:
        self._jobs: list[JobMeta] = list(jobs) if jobs else []

    def add_job(self, job: Job, interval_seconds: float | None = None) -> None:
        self._jobs.append(JobMeta(job=job, interval_seconds=interval_seconds))

    def run_pending(self, ctx: HeartbeatContext, now: float | None = None) -> None:
        now = now or time.monotonic()
        for meta in self._jobs:
            job = meta.job
            try:
                should = False
                if hasattr(job, "should_run"):
                    should = job.should_run(now, ctx.shared_state)
                elif meta.interval_seconds is not None:
                    should = meta.last_run is None or (now - meta.last_run) >= meta.interval_seconds
                if not should:
                    continue

                start = time.monotonic()
                job.run(ctx)
                duration = time.monotonic() - start
                meta.last_run = now
                ctx.logger.debug("job %s ran in %.3fs", job.name, duration)
            except Exception:  # noqa: BLE001
                ctx.logger.exception("job %s failed", getattr(job, "name", job))


def run_heartbeat(
    registry: JobRegistry,
    tick_seconds: float = 1.0,
    ctx: HeartbeatContext | None = None,
) -> None:
    """Run a simple blocking heartbeat loop.

    The caller is responsible for ensuring single-instance execution
    (e.g., Django autoreloader guard or external leader lock).
    """

    logger = (ctx.logger if ctx else None) or logging.getLogger("heartbeat")
    context = ctx or HeartbeatContext(logger=logger, shared_state={})

    logger.info("heartbeat starting (tick=%.2fs)", tick_seconds)
    while True:
        now = time.monotonic()
        registry.run_pending(context, now)

        if context.stop_event and context.stop_event.is_set():
            logger.info("heartbeat stopping on stop_event")
            break

        # Use monotonic sleep to avoid drift.
        time.sleep(tick_seconds)
