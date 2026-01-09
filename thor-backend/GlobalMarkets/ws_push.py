"""
GlobalMarkets → WebSocket broadcaster (thin wrapper)

WHAT THIS IS
------------
This module is the ONLY place where GlobalMarkets references the WebSocket layer.

WHAT THIS DOES
--------------
- Takes an already-built payload from GlobalMarkets/realtime logic
- Sends it into the single WebSocket pipeline via api.websocket.broadcast

WHAT THIS DOES NOT DO
---------------------
- Open sockets
- Run timers
- Compute market logic
- Know about consumers
- Know about channel layers

It ONLY broadcasts when called by the realtime loop (and only on status change).
"""

from typing import Any, Dict

from api.websocket.broadcast import broadcast_to_websocket_sync


# Canonical message type for global markets status updates
GLOBAL_MARKETS_MESSAGE_TYPE = "global_markets_tick"


def broadcast_global_markets_tick(payload: Dict[str, Any]) -> None:
    """
    Broadcast a single Global Markets update.

    The consumer must have a matching handler method:
        async def global_markets_tick(self, event): ...
    """
    broadcast_to_websocket_sync(
        channel_layer=None,  # helper resolves channel layer safely
        message={
            "type": GLOBAL_MARKETS_MESSAGE_TYPE,
            "data": payload,
        },
    )


# Back-compat alias: older code may call push_global_markets_tick(...)
push_global_markets_tick = broadcast_global_markets_tick
