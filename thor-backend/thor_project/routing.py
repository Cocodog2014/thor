"""
ASGI routing configuration for WebSocket connections.

Maps WebSocket URL patterns to their corresponding consumers.
All WebSocket infrastructure is in the api app.
"""

from django.urls import re_path
from api.websocket import consumers

# Accept both trailing slash variants. Some clients also connect to /ws/market-data/.
websocket_urlpatterns = [
    re_path(r"^ws/?$", consumers.MarketDataConsumer.as_asgi()),
    re_path(r"^ws/market-data/?$", consumers.MarketDataConsumer.as_asgi()),
]
