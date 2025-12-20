"""
WebSocket consumers for real-time market data streaming.

Handles WebSocket connections and broadcasts market status, intraday bars,
quotes, and other real-time data from the heartbeat scheduler.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming real-time market data.
    
    Clients connect to /ws/ endpoint and receive:
    - Market status updates (open/closed)
    - Intraday 1-minute OHLCV bars
    - Quote ticks (price, volume, bid/ask)
    - 24-hour statistics
    - VWAP values
    - Heartbeat messages
    - Error messages
    
    Message Format (from frontend spec):
    {
        "type": "intraday_bar" | "market_status" | "quote_tick" | "heartbeat" | etc.,
        "data": { ...message-specific fields... }
    }
    """
    
    async def connect(self):
        """
        Called when a WebSocket connection is established.
        Joins the broadcast channel layer if available.
        """
        # Join the market data broadcast group if channel layer is configured
        if self.channel_layer:
            try:
                await self.channel_layer.group_add("market_data", self.channel_name)
            except AttributeError:
                pass  # channel_name may not be available in all test scenarios
        
        await self.accept()
        logger.debug("WebSocket client connected")
    
    async def disconnect(self, close_code):
        """
        Called when a WebSocket connection is closed.
        Removes the client from broadcast groups.
        """
        # Leave the market data broadcast group if channel layer is configured
        if self.channel_layer:
            try:
                await self.channel_layer.group_discard("market_data", self.channel_name)
            except AttributeError:
                pass  # channel_name may not be available in all test scenarios
        logger.debug("WebSocket client disconnected")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Called when data is received from the WebSocket.
        Currently used for heartbeat acknowledgments (optional).
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get("type")
                
                # Handle client-side heartbeat ACK or ping messages
                if message_type == "ping":
                    await self.send(text_data=json.dumps({
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    }))
                else:
                    logger.debug(f"Received message from client: {message_type}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client")
    
    # ---- Broadcast message handlers ----
    # These methods are called by the channel layer when messages are sent
    # to the "market_data" group. Method name must match message["type"].
    
    async def intraday_bar(self, event):
        """Broadcast intraday bar update to client."""
        await self.send(text_data=json.dumps({
            "type": "intraday_bar",
            "data": event.get("data")
        }))
    
    async def market_status(self, event):
        """Broadcast market status update to client."""
        await self.send(text_data=json.dumps({
            "type": "market_status",
            "data": event.get("data")
        }))
    
    async def quote_tick(self, event):
        """Broadcast quote tick update to client."""
        await self.send(text_data=json.dumps({
            "type": "quote_tick",
            "data": event.get("data")
        }))
    
    async def twenty_four_hour(self, event):
        """Broadcast 24-hour statistics update to client."""
        await self.send(text_data=json.dumps({
            "type": "twenty_four_hour",
            "data": event.get("data")
        }))
    
    async def vwap_update(self, event):
        """Broadcast VWAP update to client."""
        await self.send(text_data=json.dumps({
            "type": "vwap_update",
            "data": event.get("data")
        }))
    
    async def heartbeat(self, event):
        """Broadcast heartbeat message to client."""
        await self.send(text_data=json.dumps({
            "type": "heartbeat",
            "data": event.get("data")
        }))

    async def global_markets_tick(self, event):
        """Broadcast consolidated per-market clock tick to client."""
        await self.send(text_data=json.dumps({
            "type": "global_markets_tick",
            "data": event.get("data")
        }))
    
    async def error_message(self, event):
        """Broadcast error message to client."""
        await self.send(text_data=json.dumps({
            "type": "error_message",
            "data": event.get("data")
        }))
