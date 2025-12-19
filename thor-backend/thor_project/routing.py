"""
ASGI routing configuration for WebSocket connections.

Maps WebSocket URL patterns to their corresponding consumers.
"""

from django.urls import path
from GlobalMarkets import consumers

websocket_urlpatterns = [
    path("ws/", consumers.MarketDataConsumer.as_asgi()),
]
