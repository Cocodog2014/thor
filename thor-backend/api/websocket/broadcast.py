"""
WebSocket Broadcasting Helpers

All WebSocket broadcast functionality centralized here.
Domain apps call these to broadcast their data without knowing about WebSocket internals.
"""

import asyncio
import logging
import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

DEFAULT_GROUP_NAME = "market_data"


def _market_data_debug_enabled() -> bool:
    return os.getenv("THOR_DEBUG_MARKET_DATA", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_market_data_send(group_name: str, msg_type: str | None) -> None:
    if group_name != DEFAULT_GROUP_NAME or not _market_data_debug_enabled():
        return

    try:
        from LiveData.shared.redis_client import live_data_redis as r
    except Exception:
        return

    try:
        pid = os.getpid()
        r.client.sadd("debug:market_data_pids", pid)
        r.client.set("debug:market_data_last_pid", pid)
        if msg_type:
            r.client.set("debug:market_data_last_type", msg_type)
            r.client.expire("debug:market_data_last_type", 300)

        r.client.incr("debug:market_data_sends")
        r.client.expire("debug:market_data_sends", 60)

        per_pid_key = f"debug:market_data_sends:{pid}"
        r.client.incr(per_pid_key)
        r.client.expire(per_pid_key, 60)
    except Exception:
        logger.debug("market_data debug counter failed", exc_info=True)


def _json_safe(value: Any) -> Any:
    """Recursively convert objects to msgpack/json-safe primitives."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    # Last resort: stringify unknown objects
    return str(value)


async def broadcast_to_websocket_async(message: Dict[str, Any], group_name: str = DEFAULT_GROUP_NAME) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    safe_message = _json_safe(message)

    try:
        msg_type = safe_message.get("type")
        logger.debug("📡 Broadcasting to WebSocket (async): %s", msg_type)

        if group_name == DEFAULT_GROUP_NAME and _market_data_debug_enabled():
            await asyncio.to_thread(_debug_market_data_send, group_name, msg_type)

        await channel_layer.group_send(group_name, safe_message)
        logger.debug("✅ WebSocket broadcast sent (async): %s", msg_type)
    except Exception:
        logger.exception("❌ WebSocket broadcast error (async)")


def broadcast_to_websocket_sync(
    channel_layer: Optional[Any],
    message: Dict[str, Any],
    group_name: str = DEFAULT_GROUP_NAME
) -> None:
    """
    Safe to call from:
      - normal sync threads (no running loop) -> uses async_to_sync
      - inside an asyncio loop thread (e.g., Schwab streamer) -> schedules create_task
    """
    channel_layer = channel_layer or get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    safe_message = _json_safe(message)
    msg_type = safe_message.get("type")

    try:
        _debug_market_data_send(group_name, msg_type)

        # If we are already inside an event loop thread, schedule the send
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(channel_layer.group_send(group_name, safe_message))
            logger.debug("✅ WebSocket broadcast scheduled on loop: %s", msg_type)
            return

        # No running loop in this thread -> bridge safely
        async_to_sync(channel_layer.group_send)(group_name, safe_message)
        logger.debug("✅ WebSocket broadcast sent (sync bridge): %s", msg_type)

    except Exception:
        # Never let WebSocket errors block the calling code
        logger.exception("❌ WebSocket broadcast error")
