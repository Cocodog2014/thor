"""Shared helpers for normalizing market country identifiers."""

from __future__ import annotations

from typing import Optional

# Canonical outputs map to the values expected by downstream services.
# Alias keys should be uppercase for easier comparison.
COUNTRY_CODE_MAP = {
    "USA": "USA",
    "UNITED STATES": "USA",
    "US": "USA",
    "AMERICA": "USA",
    "PRE_USA": "Pre_USA",
    "PRE-USA": "Pre_USA",
    "PRE USA": "Pre_USA",
    "JAPAN": "JP",
    "JP": "JP",
    "CHINA": "CN",
    "CN": "CN",
    "INDIA": "IN",
    "IN": "IN",
    "UNITED KINGDOM": "UK",
    "GREAT BRITAIN": "UK",
    "ENGLAND": "UK",
    "UK": "UK",
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
