"""Infrastructure heartbeat loop.

Single timer that dispatches registered jobs. Keep this file free of
domain-specific imports or logic.

Uses JobRegistry from core/infra/jobs.py (single source of truth).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
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
    """Run a simple blocking heartbeat loop.

    Args:
        registry: JobRegistry with all registered jobs (from core/infra/jobs.py).
        tick_seconds: Default tick interval in seconds.
        tick_seconds_fn: Optional callable to dynamically select tick per iteration.
        ctx: Optional HeartbeatContext; will be created if not provided.
        channel_layer: Optional Channels layer for WebSocket broadcasting (shadow mode).
        leader_lock: Optional leader lock with renew_if_due() for multi-worker safety.

    The caller is responsible for ensuring single-instance execution
    (e.g., Django autoreloader guard or external leader lock).
    """
    logger = (ctx.logger if ctx else None) or logging.getLogger("heartbeat")
    context = ctx or HeartbeatContext(logger=logger, shared_state={})

    # Add channel layer to context if provided
    if channel_layer and not context.channel_layer:
        context.channel_layer = channel_layer

    logger.info("heartbeat starting (tick=%.2fs)", tick_seconds)
    current_tick = tick_seconds
    tick_count = 0

    while True:
        tick_count += 1

        # Renew leader lock if provided (must be same thread that acquired it)
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

        # Broadcast heartbeat every tick (~1s default) with UTC time
        if context.channel_layer:
            try:
                from api.websocket.broadcast import broadcast_to_websocket_sync
                from api.websocket.messages import (
                    build_account_balance_message,
                    build_market_status_message,
                )

                now_ts = time.time()
                heartbeat_msg = {
                    "type": "heartbeat",
                    "data": {
                        "timestamp": now_ts,
                        "utc_iso": datetime.now(timezone.utc).isoformat(),
                        "stale_after_seconds": 5,
                    },
                }
                broadcast_to_websocket_sync(context.channel_layer, heartbeat_msg)
            except Exception as e:
                logger.debug("WebSocket heartbeat broadcast failed: %s", e)

        # Broadcast richer data every 5 ticks (~5 seconds)
        if tick_count % 5 == 0 and context.channel_layer:
            if context.channel_layer:
                try:
                    from api.websocket.broadcast import broadcast_to_websocket_sync
                    from api.websocket.messages import (
                        build_account_balance_message,
                        build_market_status_message,
                    )
                    
                    # 1. Broadcast account balance (for TEST-001)
                    try:
                        from ActAndPos.models import Account
                        account = Account.objects.filter(account_id="TEST-001").first()
                        if account:
                            balance_data = {
                                "account_id": account.account_id,
                                "cash": float(account.cash or 0),
                                "portfolio_value": float(account.net_liq or 0),
                                "buying_power": float(account.buying_power or 0),
                                "equity": float(account.equity or 0),
                                "timestamp": time.time(),
                            }
                            balance_msg = build_account_balance_message(balance_data)
                            broadcast_to_websocket_sync(context.channel_layer, balance_msg)
                    except Exception as e:
                        logger.debug("Account balance broadcast failed: %s", e)
                    
                    # 2. Broadcast market status and per-market clock tick for active markets
                    try:
                        from GlobalMarkets.models import Market
                        markets = Market.objects.filter(is_active=True)
                        market_ticks = []
                        for market in markets:
                            try:
                                status_data = market.get_market_status()
                                if status_data:
                                    # Ensure current_time is always present for frontend clocks
                                    status_data.setdefault("current_time", time.time())
                                    market_data = {
                                        "market_id": market.id,
                                        "country": market.country,
                                        "status": market.status,
                                        "market_status": status_data,
                                        "current_time": status_data.get("current_time"),
                                    }
                                    market_msg = build_market_status_message(market_data)
                                    broadcast_to_websocket_sync(context.channel_layer, market_msg)

                                    market_ticks.append({
                                        "market_id": market.id,
                                        "country": market.country,
                                        "current_time": status_data.get("current_time"),
                                    })
                            except Exception as e:
                                logger.debug("Market status broadcast failed for %s: %s", market.country, e)

                        # Broadcast consolidated per-market clock tick
                        if market_ticks:
                            tick_msg = {
                                "type": "global_markets_tick",
                                "data": {
                                    "timestamp": time.time(),
                                    "markets": market_ticks,
                                },
                            }
                            broadcast_to_websocket_sync(context.channel_layer, tick_msg)
                    except Exception as e:
                        logger.debug("Market status broadcast failed: %s", e)
                        
                except Exception as e:
                    logger.debug("WebSocket broadcast failed: %s", e)
        
        # Periodic heartbeat alive log (low noise - every 30 ticks)
        if tick_count % 30 == 0:
            logger.info("💓 Heartbeat alive (tick=%s, tick_seconds=%s)", tick_count, current_tick)

        # Use monotonic sleep to avoid drift.
        time.sleep(current_tick)
