"""Compatibility shim for MarketGraderJob location change.

Use ThorTrading.realtime.jobs.market_grader instead of this module.
"""

from ThorTrading.realtime.jobs.market_grader import MarketGraderJob  # noqa: F401

__all__ = ["MarketGraderJob"]
