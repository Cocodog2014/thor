"""
GlobalMarkets → WebSocket broadcaster

PURPOSE
-------
This module is the ONLY place where the GlobalMarkets app touches WebSockets.

It does NOT:
- open sockets
- run timers
- compute market logic
- know about consumers
- know about channel layers

It ONLY sends a message when GlobalMarkets decides a status changed.
"""

from typing import Dict, Any
from api.websocket.broadcast import broadcast_to_websocket_sync


def broadcast_global_markets_tick(payload: Dict[str, Any]) -> None:
    """
    Broadcast a single Global Markets status update.

    This MUST be called ONLY when a market status actually changes
    (ex: US opens, JP closes).

    The message type MUST match the consumer handler:
        MarketDataConsumer.global_markets_tick(...)
    """

    broadcast_to_websocket_sync(
        channel_layer=None,   # let the helper resolve it safely
        message={
            "type": "global_markets_tick",
            "data": payload,
        },
    )

