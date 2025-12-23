"""Centralized constants for FutureTrading app.

Provides single source of truth for:
- Futures symbols tracked
- Control market country list (aligned with GlobalMarkets)
- Redis/Excel symbol mappings to canonical futures symbols
- Symbol normalization map (all sources → canonical form)
"""

from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES

FUTURES_SYMBOLS = [
    'YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB'
]

# Order matters for east→west control flow (mirrors GlobalMarkets)
_CONTROL_ORDER = [
    'Japan', 'China', 'India', 'Germany', 'United Kingdom',
    'Pre_USA', 'USA', 'Canada', 'Mexico'
]
# Preserve east→west ordering while deriving from the canonical allowed set.
CONTROL_COUNTRIES = [c for c in _CONTROL_ORDER if c in ALLOWED_CONTROL_COUNTRIES]

# Mapping from canonical symbol to Redis key (or other external feed key)
REDIS_SYMBOL_MAP = {
    'DX': '$DXY',  # Dollar Index in Redis/Excel
}

# Comprehensive normalization: any alias/external variant → canonical symbol
SYMBOL_NORMALIZE_MAP = {
    # Russell
    'RT': 'RTY', 'RTY': 'RTY',
    # Bond
    '30YrBond': 'ZB', '30Yr T-BOND': 'ZB', 'T-BOND': 'ZB', 'ZB': 'ZB',
    # Dollar index variants
    '$DXY': 'DX', 'DXY': 'DX', 'USDX': 'DX', 'DX': 'DX',
}

__all__ = [
    'FUTURES_SYMBOLS',
    'CONTROL_COUNTRIES',
    'REDIS_SYMBOL_MAP',
    'SYMBOL_NORMALIZE_MAP',
]
