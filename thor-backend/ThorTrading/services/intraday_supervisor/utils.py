"""
Utility functions for intraday supervisor.

This module provides shared utilities for converting and processing market data.

Used by:
- intraday_bars.py: Converts bid/ask/last/spread prices to Decimal when creating 1-minute OHLCV bars
- feed_24h.py: Converts open/close/high/low prices and calculates 24-hour range metrics

Key function:
- safe_decimal(): Safely converts price values to Decimal, handling None/empty/invalid values
"""

from decimal import Decimal as D

def safe_decimal(val):
    """
    Safely convert a value to Decimal.
    
    Args:
        val: Price value (float, int, string, Decimal, or None)
    
    Returns:
        Decimal instance or None if value is invalid/empty
    
    Examples:
        safe_decimal(100.5) -> Decimal('100.5')
        safe_decimal('99.99') -> Decimal('99.99')
        safe_decimal(None) -> None
        safe_decimal('') -> None
        safe_decimal('invalid') -> None
    """
    if val in (None, '', ' '):
        return None
    try:
        return D(str(val))
    except Exception:
        return None

