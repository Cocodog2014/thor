"""Canonical market key helpers shared across Thor services.

Keep this aligned with GlobalMarkets.ALLOWED_CONTROL_COUNTRIES so DB, Redis,
WS payloads, and UI use the same identifiers.
"""
from __future__ import annotations

from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES
from ThorTrading.services.country_codes import normalize_country_code

# East→west ordering used in GlobalMarkets views and UI tables.
CANONICAL_ORDER = (
    "Japan",
    "China",
    "India",
    "Germany",
    "United Kingdom",
    "Pre_USA",
    "USA",
    "Canada",
    "Mexico",
    "Futures",
)

CANONICAL_MARKET_KEYS = CANONICAL_ORDER
_CANONICAL_MAP = {c.lower(): c for c in ALLOWED_CONTROL_COUNTRIES}

MARKET_DISPLAY_NAMES = {
    "Japan": "Tokyo",
    "China": "Shanghai",
    "India": "Bombay",
    "Germany": "Frankfurt",
    "United Kingdom": "London",
    "Pre_USA": "Pre_USA",
    "USA": "USA",
    "Canada": "Toronto",
    "Mexico": "Mexican",
    "Futures": "CME Futures (GLOBEX)",
}


def normalize_market_key(raw: str | None) -> str | None:
    """Return canonical market key or None if unknown."""
    if raw is None:
        return None
    normalized = normalize_country_code(raw)
    if not normalized:
        return normalized
    return _CANONICAL_MAP.get(normalized.lower())


def display_name_for_market(key: str) -> str:
    return MARKET_DISPLAY_NAMES.get(key, key)


__all__ = [
    "CANONICAL_MARKET_KEYS",
    "MARKET_DISPLAY_NAMES",
    "normalize_market_key",
    "display_name_for_market",
]
