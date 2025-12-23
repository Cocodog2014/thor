"""Legacy views package placeholder. Use ThorTrading.api.views instead."""

from ThorTrading.services.runtime_guard import assert_heartbeat_mode

assert_heartbeat_mode()

raise RuntimeError("Legacy views package removed; use ThorTrading.api.views")

