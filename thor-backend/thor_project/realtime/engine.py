"""Realtime heartbeat engine (single scheduler loop)."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from core.infra.jobs import JobRegistry
from thor_project.realtime import broadcaster


@dataclass
class HeartbeatContext:
    logger: logging.Logger
    shared_state: dict[str, Any]
    settings: Any | None = None
    stop_event: threading.Event | None = None
    channel_layer: Any | None = None  # For WebSocket broadcasting


def run_heartbeat(
    registry: JobRegistry,
    tick_seconds: float = 1.0,
    tick_seconds_fn: Callable[[HeartbeatContext], float] | None = None,
    ctx: HeartbeatContext | None = None,
    channel_layer: Any | None = None,
    leader_lock: Any | None = None,
) -> None:
    """Run the blocking heartbeat loop that dispatches registered jobs."""
    logger = (ctx.logger if ctx else None) or logging.getLogger("heartbeat")
    context = ctx or HeartbeatContext(logger=logger, shared_state={})

    if channel_layer and not context.channel_layer:
        context.channel_layer = channel_layer

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

        if tick_seconds_fn:
            try:
                current_tick = float(tick_seconds_fn(context))
            except Exception:
                logger.exception(
                    "tick_seconds_fn failed; keeping previous tick=%.2f", current_tick
                )
        if current_tick <= 0:
            logger.warning(
                "invalid tick %.3f; falling back to default %.2f",
                current_tick,
                tick_seconds,
            )
            current_tick = tick_seconds

        if context.channel_layer:
            broadcaster.broadcast_heartbeat_tick(context.channel_layer, logger)
            broadcaster.broadcast_market_clocks(context.channel_layer, logger)

        if tick_count % 5 == 0 and context.channel_layer:
            broadcaster.broadcast_account_and_status(context.channel_layer, logger)

        if tick_count % 30 == 0:
            logger.info("💓 Heartbeat alive (tick=%s, tick_seconds=%s)", tick_count, current_tick)

        time.sleep(current_tick)


__all__ = ["HeartbeatContext", "run_heartbeat"]
