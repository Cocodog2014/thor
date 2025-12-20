"""
ASGI routing configuration for WebSocket connections.

Maps WebSocket URL patterns to their corresponding consumers.
All WebSocket infrastructure is in the api app.
"""

from django.urls import re_path
from api.websocket import consumers

# Accept both /ws/ and /ws (browser variances). Using re_path keeps compatibility.
websocket_urlpatterns = [
    re_path(r"^ws/$", consumers.MarketDataConsumer.as_asgi()),
    re_path(r"^ws$", consumers.MarketDataConsumer.as_asgi()),
]
