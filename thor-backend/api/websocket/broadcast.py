"""
WebSocket Broadcasting Helpers

All WebSocket broadcast functionality centralized here.
Domain apps call these to broadcast their data without knowing about WebSocket internals.
"""

import asyncio
import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict

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


async def broadcast_to_websocket_async(message: Dict[str, Any], group_name: str = DEFAULT_GROUP_NAME) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    try:
        msg_type = message.get("type")
        logger.debug("📡 Broadcasting to WebSocket (async): %s", msg_type)
        await channel_layer.group_send(group_name, _json_safe(message))
        logger.debug("✅ WebSocket broadcast sent (async): %s", msg_type)
    except Exception:
        logger.exception("❌ WebSocket broadcast error (async)")


def broadcast_to_websocket_sync(channel_layer: Any, message: Dict[str, Any], group_name: str = DEFAULT_GROUP_NAME) -> None:
    """
    Safe to call from:
      - normal sync threads (no running loop) -> uses async_to_sync
      - inside an asyncio loop thread (e.g., Schwab streamer) -> schedules create_task
    """
    channel_layer = channel_layer or get_channel_layer()
    if not channel_layer:
        logger.warning("No channel_layer available - skipping WebSocket broadcast")
        return

    try:
            safe_message = _json_safe(message)
        msg_type = message.get("type")
        logger.debug("📡 Broadcasting to WebSocket: %s", msg_type)

        try:
            loop = asyncio.get_running_loop()
                async_to_sync(channel_layer.group_send)(group_name, safe_message)
            # No running loop in this thread -> safe to bridge
            async_to_sync(channel_layer.group_send)(group_name, message)
            logger.debug("✅ WebSocket broadcast sent (sync bridge): %s", msg_type)
            return
            loop.create_task(channel_layer.group_send(group_name, safe_message))
        # Running inside an event loop thread -> avoid async_to_sync
        loop.create_task(channel_layer.group_send(group_name, message))
        logger.debug("✅ WebSocket broadcast scheduled on loop: %s", msg_type)
    except Exception:
        # Never let WebSocket errors block the calling code
        logger.exception("❌ WebSocket broadcast error")
