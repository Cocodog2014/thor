"""Neutral job registry: register jobs and run those that are due.

No domain imports here. Shared state tracks last_run per job name.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol


class Job(Protocol):
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
        self.jobs.append(JobEntry(job=job, interval_seconds=interval_seconds))

    def run_pending(self, ctx: Any, now: float | None = None) -> None:
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
