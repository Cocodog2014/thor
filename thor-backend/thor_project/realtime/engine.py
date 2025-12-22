"""Realtime heartbeat engine (single scheduler loop)."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from core.infra.jobs import JobRegistry


@dataclass
class HeartbeatContext:
    logger: logging.Logger
    shared_state: dict[str, Any]
    settings: Any | None = None
    stop_event: threading.Event | None = None
    channel_layer: Any | None = None  # Passed to jobs that need it


def run_heartbeat(
    registry: JobRegistry,
    tick_seconds: float = 1.0,
    ctx: HeartbeatContext | None = None,
    channel_layer: Any | None = None,
    leader_lock: Any | None = None,
) -> None:
    """Run the blocking heartbeat loop that dispatches registered jobs."""
    logger = (ctx.logger if ctx else None) or logging.getLogger("heartbeat")
    context = ctx or HeartbeatContext(logger=logger, shared_state={})

    if channel_layer and not context.channel_layer:
        context.channel_layer = channel_layer

    # Force a 1s cadence for now (can be revisited later)
    tick_seconds = 1.0
    logger.info("heartbeat starting (tick=%.2fs)", tick_seconds)
    current_tick = tick_seconds
    tick_count = 0

    while True:
        tick_count += 1

        if leader_lock and hasattr(leader_lock, "renew_if_due"):
            if not leader_lock.renew_if_due():
                logger.error("heartbeat lost leader lock; stopping")
                break

        now = time.monotonic()
        registry.run_pending(context, now)

        if context.stop_event and context.stop_event.is_set():
            logger.info("heartbeat stopping on stop_event")
            break

        # keep tick fixed at 1s for now
        current_tick = tick_seconds

        if tick_count % 30 == 0:
            logger.info("💓 Heartbeat alive (tick=%s, tick_seconds=%s)", tick_count, current_tick)

        # Use stop_event-aware wait to exit promptly on shutdown
        if context.stop_event:
            if context.stop_event.wait(timeout=current_tick):
                logger.info("heartbeat stopping on stop_event (wait)")
                break
        else:
            time.sleep(current_tick)


__all__ = ["HeartbeatContext", "run_heartbeat"]
