"""
WebSocket Broadcasting Helpers

All WebSocket broadcast functionality centralized here.
Domain apps call these to broadcast their data without knowing about WebSocket internals.
"""

import asyncio
import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple, Union

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

DEFAULT_GROUP_NAME = "market_data"


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


async def broadcast_to_websocket_async(
    message: Dict[str, Any],
    group_name: str = DEFAULT_GROUP_NAME,
) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    try:
        safe_message = _json_safe(message)
        msg_type = message.get("type")
        logger.debug("📡 Broadcasting to WebSocket (async): %s", msg_type)
        await channel_layer.group_send(group_name, safe_message)
        logger.debug("✅ WebSocket broadcast sent (async): %s", msg_type)
    except Exception:
        logger.exception("❌ WebSocket broadcast error (async)")


def _normalize_sync_args(*args: Any, **kwargs: Any) -> Tuple[Any, Dict[str, Any], str]:
    """
    Backward-compatible argument normalization.

    Supports:
      - broadcast_to_websocket_sync(message)
      - broadcast_to_websocket_sync(message, group_name="...")
      - broadcast_to_websocket_sync(group_name, message)
      - broadcast_to_websocket_sync(channel_layer, message, group_name="...")
    """
    group_name = kwargs.get("group_name", DEFAULT_GROUP_NAME)
    channel_layer = kwargs.get("channel_layer", None)

    if len(args) == 1:
        # (message,)
        message = args[0]
        return channel_layer, message, group_name

    if len(args) == 2:
        # Could be (group_name, message) OR (channel_layer, message) OR (message, group_name)
        a0, a1 = args[0], args[1]

        if isinstance(a0, str) and isinstance(a1, dict):
            # (group_name, message)
            return channel_layer, a1, a0

        if isinstance(a0, dict) and isinstance(a1, str):
            # (message, group_name)
            return channel_layer, a0, a1

        # (channel_layer, message)
        return a0, a1, group_name

    if len(args) >= 3:
        # (channel_layer, message, group_name)
        return args[0], args[1], args[2]

    raise TypeError("broadcast_to_websocket_sync requires at least a message")


def broadcast_to_websocket_sync(*args: Any, **kwargs: Any) -> None:
    """
    Safe to call from:
      - normal sync threads (no running loop) -> uses async_to_sync
      - inside an asyncio loop thread (e.g., Schwab streamer) -> schedules create_task

    Backward-compatible signature (see _normalize_sync_args).
    """
    channel_layer, message, group_name = _normalize_sync_args(*args, **kwargs)

    channel_layer = channel_layer or get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    try:
        safe_message = _json_safe(message)
        msg_type = message.get("type") if isinstance(message, dict) else None
        logger.debug("📡 Broadcasting to WebSocket: %s", msg_type)

        try:
            # If we're in an async thread with a running loop, do NOT use async_to_sync.
            loop = asyncio.get_running_loop()
            loop.create_task(channel_layer.group_send(group_name, safe_message))
            logger.debug("✅ WebSocket broadcast scheduled on loop: %s", msg_type)
        except RuntimeError:
            # No running loop -> safe sync bridge
            async_to_sync(channel_layer.group_send)(group_name, safe_message)
            logger.debug("✅ WebSocket broadcast sent (sync bridge): %s", msg_type)

    except Exception:
        # Never let WebSocket errors block the calling code
        logger.exception("❌ WebSocket broadcast error")

