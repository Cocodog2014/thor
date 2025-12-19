"""Infrastructure heartbeat loop.

Single timer that dispatches registered jobs. Keep this file free of
domain-specific imports or logic.

Uses JobRegistry from core/infra/jobs.py (single source of truth).
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from core.infra.jobs import JobRegistry


@dataclass
class HeartbeatContext:
    logger: logging.Logger
    shared_state: dict[str, Any]
    settings: Any | None = None
    stop_event: threading.Event | None = None


def run_heartbeat(
    registry: JobRegistry,
    tick_seconds: float = 1.0,
    tick_seconds_fn: Callable[[HeartbeatContext], float] | None = None,
    ctx: HeartbeatContext | None = None,
) -> None:
    """Run a simple blocking heartbeat loop.

    Args:
        registry: JobRegistry with all registered jobs (from core/infra/jobs.py).
        tick_seconds: Default tick interval in seconds.
        tick_seconds_fn: Optional callable to dynamically select tick per iteration.
        ctx: Optional HeartbeatContext; will be created if not provided.

    The caller is responsible for ensuring single-instance execution
    (e.g., Django autoreloader guard or external leader lock).
    """

    logger = (ctx.logger if ctx else None) or logging.getLogger("heartbeat")
    context = ctx or HeartbeatContext(logger=logger, shared_state={})

    logger.info("heartbeat starting (tick=%.2fs)", tick_seconds)
    current_tick = tick_seconds
    while True:
        now = time.monotonic()
        registry.run_pending(context, now)

        if context.stop_event and context.stop_event.is_set():
            logger.info("heartbeat stopping on stop_event")
            break

        if tick_seconds_fn:
            try:
                current_tick = float(tick_seconds_fn(context))
            except Exception:
                logger.exception("tick_seconds_fn failed; keeping previous tick=%.2f", current_tick)
        if current_tick <= 0:
            logger.warning("invalid tick %.3f; falling back to default %.2f", current_tick, tick_seconds)
            current_tick = tick_seconds

        # Use monotonic sleep to avoid drift.
        time.sleep(current_tick)
