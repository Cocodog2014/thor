"""Legacy module placeholder.

Use ThorTrading.api.views.market_grader instead.
"""
from ThorTrading.services.runtime_guard import assert_heartbeat_mode

assert_heartbeat_mode()

raise RuntimeError("Legacy MarketGrader module removed; use ThorTrading.api.views.market_grader")

