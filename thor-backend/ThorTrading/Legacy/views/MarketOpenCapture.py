"""Legacy placeholder for MarketOpenCapture.

Use ThorTrading.api.views.market_open instead.
"""
from ThorTrading.services.runtime_guard import assert_heartbeat_mode

assert_heartbeat_mode()

raise RuntimeError("Legacy MarketOpenCapture module removed; use ThorTrading.api.views.market_open")
