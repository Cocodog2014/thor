"""
WebSocket URL routing
"""

from django.urls import path
from api.websocket.consumers import MarketDataConsumer

websocket_urlpatterns = [
    # Support the Watchlist specific path
    path('ws/market-data/', MarketDataConsumer.as_asgi()),

    # Support the Global App (socket.ts) path
    path('ws/', MarketDataConsumer.as_asgi()),
]
