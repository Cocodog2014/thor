"""
WebSocket Broadcasting Helpers

All WebSocket broadcast functionality centralized here.
Domain apps call these to broadcast their data without knowing about WebSocket internals.
"""

import logging
from typing import Any, Dict

from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

DEFAULT_GROUP_NAME = "market_data"


def broadcast_to_websocket_sync(channel_layer: Any, message: Dict[str, Any], group_name: str = DEFAULT_GROUP_NAME) -> None:
    """
    Sync-safe broadcast to Channels group.

    - Does NOT create event loops.
    - Safe to call from sync code (heartbeat thread, Django views, mgmt commands).
    """
    if not channel_layer:
        logger.warning("No channel_layer provided - skipping WebSocket broadcast")
        return

    try:
        msg_type = message.get("type")
        logger.debug("📡 Broadcasting to WebSocket: %s", msg_type)
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.debug("✅ WebSocket broadcast sent: %s", msg_type)
    except Exception:
        # Never let WebSocket errors block the calling code
        logger.exception("❌ WebSocket broadcast error")


async def broadcast_to_websocket(channel_layer: Any, message: Dict[str, Any], group_name: str = DEFAULT_GROUP_NAME) -> None:
    """
    Async broadcast to Channels group.
    Use in async code (consumers, async views).
    """
    if not channel_layer:
        logger.warning("No channel_layer provided - skipping WebSocket broadcast")
        return

    try:
        msg_type = message.get("type")
        logger.debug("📡 Broadcasting to WebSocket (async): %s", msg_type)
        await channel_layer.group_send(group_name, message)
        logger.debug("✅ WebSocket broadcast sent (async): %s", msg_type)
    except Exception:
        logger.exception("❌ WebSocket broadcast error (async)")
