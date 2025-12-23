"""Legacy module placeholder.

Use ThorTrading.api.views.market_sessions instead.
"""
from ThorTrading.services.runtime_guard import assert_heartbeat_mode

assert_heartbeat_mode()

raise RuntimeError("Legacy MarketSession module removed; use ThorTrading.api.views.market_sessions")

