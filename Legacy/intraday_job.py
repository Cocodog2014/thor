"""Compatibility shim for IntradayJob location change.

Use ThorTrading.realtime.jobs.intraday_tick instead of this module.
"""

from ThorTrading.realtime.jobs.intraday_tick import IntradayJob  # noqa: F401
