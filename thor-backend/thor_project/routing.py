"""
ASGI routing configuration for WebSocket connections.

Maps WebSocket URL patterns to their corresponding consumers.
All WebSocket infrastructure is in the api app.
"""

from django.urls import path
from api.websocket import consumers

websocket_urlpatterns = [
    path("ws/", consumers.MarketDataConsumer.as_asgi()),
]
