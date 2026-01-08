"""
Country code normalization utilities.

IMPORTANT:
- This module must be import-safe during Django startup.
- Do NOT import Django models or touch the ORM here.
"""

from typing import Optional


COUNTRY_CODE_MAP = {
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "GB": "GB",
    "UK": "GB",
    "UNITED KINGDOM": "GB",
    "CA": "CA",
    "CANADA": "CA",
    "DE": "DE",
    "GERMANY": "DE",
    "FR": "FR",
    "FRANCE": "FR",
    "JP": "JP",
    "JAPAN": "JP",
    "AU": "AU",
    "AUSTRALIA": "AU",
    "GLOBAL": "GLOBAL",
}

KNOWN_COUNTRIES = set(COUNTRY_CODE_MAP.values())


def normalize_country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None
    code = str(country).upper().strip()
    return COUNTRY_CODE_MAP.get(code, None)


def is_known_country(country: Optional[str]) -> bool:
    if not country:
        return False
    normalized = normalize_country_code(country)
    return normalized is not None and normalized in KNOWN_COUNTRIES
