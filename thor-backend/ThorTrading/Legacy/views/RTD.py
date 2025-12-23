"""Legacy placeholder for RTD views.

Use ThorTrading.api.views.quotes instead.
"""
from ThorTrading.services.runtime_guard import assert_heartbeat_mode

assert_heartbeat_mode()

raise RuntimeError("Legacy RTD module removed; use ThorTrading.api.views.quotes")
