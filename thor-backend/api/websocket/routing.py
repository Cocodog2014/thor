"""
WebSocket URL routing
"""

from django.urls import path
from api.websocket.consumers import MarketDataConsumer

websocket_urlpatterns = [
    path('ws/market-data/', MarketDataConsumer.as_asgi()),
]
