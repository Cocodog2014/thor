"""Shared helpers for normalizing market country identifiers."""

from __future__ import annotations

from typing import Optional
from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES

COUNTRY_CODE_MAP = {
    "USA": "USA",
    "UNITED STATES": "USA",
    "US": "USA",
    "AMERICA": "USA",
    "PRE_USA": "Pre_USA",
    "PRE-USA": "Pre_USA",
    "PRE USA": "Pre_USA",
    "JAPAN": "Japan",
    "JP": "Japan",
    "CHINA": "China",
    "CN": "China",
    "INDIA": "India",
    "IN": "India",
    "UNITED KINGDOM": "United Kingdom",
    "GREAT BRITAIN": "United Kingdom",
    "ENGLAND": "United Kingdom",
    "UK": "United Kingdom",
    "GERMANY": "Germany",
    "DE": "Germany",
    "CANADA": "Canada",
    "CA": "Canada",
    "MEXICO": "Mexico",
    "MX": "Mexico",
}

CANONICAL_LOWER = {c.lower(): c for c in ALLOWED_CONTROL_COUNTRIES}


def normalize_country_code(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None

    trimmed = raw.strip()
    if not trimmed:
        return trimmed

    lookup = COUNTRY_CODE_MAP.get(trimmed.upper())
    if lookup:
        return lookup

    canon = CANONICAL_LOWER.get(trimmed.lower())
    if canon:
        return canon

    return trimmed.upper()


def is_known_country(raw: Optional[str], *, controlled: set[str]) -> bool:
    normalized = normalize_country_code(raw)
    if normalized is None:
        return False
    if normalized in controlled:
        return True
    return raw in controlled if raw else False


__all__ = [
    "COUNTRY_CODE_MAP",
    "normalize_country_code",
    "is_known_country",
]
