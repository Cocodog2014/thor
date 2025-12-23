"""Compatibility shim for MarketMetricsJob location change.

Use ThorTrading.realtime.jobs.market_metrics instead of this module.
"""

from ThorTrading.realtime.jobs.market_metrics import MarketMetricsJob  # noqa: F401
