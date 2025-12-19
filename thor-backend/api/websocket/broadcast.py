"""
WebSocket Broadcasting Helpers

All WebSocket broadcast functionality centralized here.
Domain apps call these to broadcast their data without knowing about WebSocket internals.
"""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def broadcast_to_websocket_sync(channel_layer, message: Dict[str, Any]):
    """
    Synchronous wrapper for broadcasting messages to WebSocket.
    
    Creates a new event loop to run the async broadcast without blocking.
    Safe to call from synchronous code (e.g., Django jobs in domain apps).
    
    Args:
        channel_layer: Django Channels layer instance
        message: Message dictionary with 'type' and 'data' keys
    """
    if not channel_layer:
        logger.warning("No channel_layer provided - skipping WebSocket broadcast")
        return
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                channel_layer.group_send("market_data", message)
            )
        finally:
            loop.close()
    except Exception as e:
        # Never let WebSocket errors block the calling code
        logger.error(f"WebSocket broadcast error: {e}", exc_info=True)


async def broadcast_to_websocket(channel_layer, message: Dict[str, Any]):
    """
    Async broadcast to WebSocket group.
    
    Use this in async code. For sync code, use broadcast_to_websocket_sync().
    """
    if not channel_layer:
        logger.warning("No channel_layer provided - skipping WebSocket broadcast")
        return
    
    try:
        await channel_layer.group_send("market_data", message)
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}", exc_info=True)
