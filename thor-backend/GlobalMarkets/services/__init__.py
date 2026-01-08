"""GlobalMarkets services package (minimal shim).
Exports compute_market_status so legacy imports keep working.
"""

from .market_clock import compute_market_status

__all__ = ["compute_market_status"]
