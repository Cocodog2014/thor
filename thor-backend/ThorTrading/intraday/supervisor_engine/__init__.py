from __future__ import annotations

"""Legacy compatibility package.

The original intraday supervisor engine was intentionally removed.
This package remains importable to avoid crashes from stale imports,
but it only re-exports the minimal compatibility supervisor.
"""

from ThorTrading.services.intraday_supervisor.supervisor import (
    IntradayMarketSupervisor,
    intraday_market_supervisor,
)

__all__ = [
    "IntradayMarketSupervisor",
    "intraday_market_supervisor",
]
