"""Realtime heartbeat engine (single scheduler loop)."""
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

    broadcaster = None

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
            if broadcaster is None:
                from thor_project.realtime import broadcaster as _b
                broadcaster = _b

            broadcaster.broadcast_heartbeat_tick(context.channel_layer, logger)
            broadcaster.broadcast_market_clocks(context.channel_layer, logger)

            # TEMP: log per-market clock to verify real-time updates
            try:
                from GlobalMarkets.models import Market
                from GlobalMarkets.services.market_clock import get_market_time

                markets = Market.objects.filter(is_active=True)
                for market in markets:
                    mt = get_market_time(market)
                    if mt:
                        logger.info("⏰ %s | %s", market.country, mt.get("formatted_24h"))
            except Exception as exc:
                logger.debug("Clock logging failed: %s", exc)

            # GlobalMarkets-only mode: skip account/status broadcasts for now
            # if tick_count % 5 == 0:
            #     broadcaster.broadcast_account_and_status(context.channel_layer, logger)

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
