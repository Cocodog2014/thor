"""Single source of truth for job registration and execution.

Neutral job registry: register jobs and run those that are due.
No domain imports here. Shared state tracks last_run per job name.

Used by the realtime heartbeat scheduler (thor_project/realtime/engine.py) to
dispatch all periodic jobs on a unified tick. This is the only JobRegistry
implementation in the codebase.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol


class Job(Protocol):
    """Job interface: each job must have a name and run method."""
    name: str

    def run(self, ctx: Any) -> None:
        ...

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        ...


@dataclass
class JobEntry:
    job: Job
    interval_seconds: float | None = None


@dataclass
class JobRegistry:
    """Single registry for all periodic jobs in the system.
    
    Provides:
    - register(job, interval) to add jobs
    - run_pending(ctx, now) to execute jobs due on this tick
    - Shared state dict for inter-job communication
    
    All jobs run under one heartbeat loop; intervals determine cadence.
    """
    jobs: list[JobEntry] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=lambda: {"last_run": {}})
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("job_registry"))

    def __init__(
        self,
        jobs: Iterable[JobEntry] | None = None,
        shared_state: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.jobs = list(jobs) if jobs else []
        self.state = shared_state if shared_state is not None else {"last_run": {}}
        self.logger = logger or logging.getLogger("job_registry")

    def register(self, job: Job, interval_seconds: float | None = None) -> None:
        """Register a job with optional default interval (in seconds).
        
        Args:
            job: Job instance with name and run/should_run methods.
            interval_seconds: Optional default interval. Job's should_run() can override.
        """
        self.jobs.append(JobEntry(job=job, interval_seconds=interval_seconds))

    def run_pending(self, ctx: Any, now: float | None = None) -> None:
        """Execute all jobs that are due on this tick.
        
        Args:
            ctx: Context passed to each job's run() method.
            now: Current monotonic time. Computed if not provided.
        """
        now = now or time.monotonic()
        last_run_map = self.state.setdefault("last_run", {})

        for entry in self.jobs:
            job = entry.job
            try:
                should = False
                if hasattr(job, "should_run"):
                    should = job.should_run(now, self.state)
                elif entry.interval_seconds is not None:
                    last = last_run_map.get(job.name)
                    should = last is None or (now - last) >= entry.interval_seconds

                if not should:
                    continue

                start = time.monotonic()
                job.run(ctx)
                last_run_map[job.name] = now
                duration = time.monotonic() - start
                self.logger.debug("job %s ran in %.3fs", job.name, duration)
            except Exception:  # noqa: BLE001
                self.logger.exception("job %s failed", getattr(job, "name", job))
