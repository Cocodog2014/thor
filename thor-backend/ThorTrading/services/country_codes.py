"""Shared helpers for normalizing market country identifiers."""

from __future__ import annotations

from typing import Optional

# Canonical outputs map to the values expected by downstream services.
# Alias keys should be uppercase for easier comparison.
COUNTRY_CODE_MAP = {
    # Canonical display-first values (match model choices/admin filters)
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
}


def normalize_country_code(raw: Optional[str]) -> Optional[str]:
    """Normalize assorted country strings to canonical codes (e.g., JP, CN)."""
    if raw is None:
        return None

    trimmed = raw.strip()
    if not trimmed:
        return trimmed

    lookup = COUNTRY_CODE_MAP.get(trimmed.upper())
    if lookup:
        return lookup

    return trimmed.upper()


def is_known_country(raw: Optional[str], *, controlled: set[str]) -> bool:
    """Return True if the raw value maps into the controlled set."""
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
