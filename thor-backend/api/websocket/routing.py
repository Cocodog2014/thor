"""
WebSocket URL routing for the Thor backend.

This file defines WHICH WebSocket URL paths exist
and WHICH consumer handles them.

IMPORTANT:
- This file does NOT open sockets by itself
- This file does NOT create multiple connections
- This file does NOT contain business logic
- This file does NOT know anything about GlobalMarkets, trades, quotes, etc.

It only maps a URL string to a WebSocket consumer class.
"""

from django.urls import path

# Import the single WebSocket consumer used by the entire system.
# This consumer is responsible for handling:
# - connect
# - disconnect
# - sending messages to the client
#
# It does NOT compute data.
from api.websocket.consumers import MarketDataConsumer


# Django Channels looks for this variable name specifically.
# It is similar to `urlpatterns` for HTTP, but for WebSockets.
websocket_urlpatterns = [

    # This defines ONE WebSocket endpoint:
    #
    #   ws://<host>/ws/
    #
    # When a client connects to this URL:
    # - Django Channels creates ONE instance of MarketDataConsumer
    # - That instance joins the "market_data" broadcast group
    #
    # This is the SINGLE WebSocket used by the entire frontend.
    # All real-time features (global markets, quotes, balances, etc.)
    # are multiplexed over this one connection.
    #
    # Having ONE path here guarantees:
    # - No accidental multiple sockets
    # - No per-feature connections
    # - No routing ambiguity
    path('ws/', MarketDataConsumer.as_asgi()),
]

