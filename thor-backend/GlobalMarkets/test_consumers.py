"""
Tests for WebSocket consumers.

Tests MarketDataConsumer connection, message handling, and basic functionality.
"""

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from asgiref.sync import async_to_sync
from GlobalMarkets.consumers import MarketDataConsumer


class TestMarketDataConsumer(TransactionTestCase):
    """Test MarketDataConsumer WebSocket functionality."""
    
    def test_connect_and_disconnect(self):
        """Test WebSocket connection and disconnection."""
        @async_to_sync
        async def run_test():
            comm = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            connected, subprotocol = await comm.connect()
            self.assertTrue(connected)
            await comm.disconnect()
        
        run_test()
    
    def test_receive_ping_responds_with_pong(self):
        """Test consumer responds to ping messages with pong."""
        @async_to_sync
        async def run_test():
            comm = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            await comm.connect()
            
            # Send ping message
            await comm.send_json_to({"type": "ping", "timestamp": 12345})
            
            # Expect pong response
            response = await comm.receive_json_from()
            self.assertEqual(response["type"], "pong")
            self.assertEqual(response["timestamp"], 12345)
            
            await comm.disconnect()
        
        run_test()
    
    def test_receive_unknown_message(self):
        """Test consumer logs unknown message types without error."""
        @async_to_sync
        async def run_test():
            comm = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            await comm.connect()
            
            # Send unknown message type (should be logged, not cause error)
            await comm.send_json_to({"type": "unknown_msg_type", "data": "test"})
            
            # Connection should still be open
            await comm.disconnect()
        
        run_test()
    
    def test_consumer_has_all_broadcast_handlers(self):
        """Test consumer has all required broadcast message handlers."""
        # Verify consumer has methods for all message types
        self.assertTrue(hasattr(MarketDataConsumer, 'intraday_bar'))
        self.assertTrue(hasattr(MarketDataConsumer, 'market_status'))
        self.assertTrue(hasattr(MarketDataConsumer, 'quote_tick'))
        self.assertTrue(hasattr(MarketDataConsumer, 'market_data'))
        self.assertTrue(hasattr(MarketDataConsumer, 'twenty_four_hour'))
        self.assertTrue(hasattr(MarketDataConsumer, 'vwap_update'))
        self.assertTrue(hasattr(MarketDataConsumer, 'heartbeat'))
        self.assertTrue(hasattr(MarketDataConsumer, 'error_message'))
    
    def test_multiple_concurrent_connections(self):
        """Test multiple WebSocket clients can connect simultaneously."""
        @async_to_sync
        async def run_test():
            comm1 = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            comm2 = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            comm3 = WebsocketCommunicator(MarketDataConsumer.as_asgi(), "/ws/")
            
            # All should connect successfully
            connected1, _ = await comm1.connect()
            connected2, _ = await comm2.connect()
            connected3, _ = await comm3.connect()
            
            self.assertTrue(connected1)
            self.assertTrue(connected2)
            self.assertTrue(connected3)
            
            # All should disconnect successfully
            await comm1.disconnect()
            await comm2.disconnect()
            await comm3.disconnect()
        
        run_test()
