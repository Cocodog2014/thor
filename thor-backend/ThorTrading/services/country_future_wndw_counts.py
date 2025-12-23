"""Compatibility shim for WNDW totals service location change.

Use ThorTrading.services.sessions.analytics.wndw_totals instead of this module.
"""

from ThorTrading.services.sessions.analytics.wndw_totals import (  # noqa: F401
    CountryFutureWndwTotalsService,
    update_country_future_wndw_total,
)

__all__ = [
    "CountryFutureWndwTotalsService",
    "update_country_future_wndw_total",
]

