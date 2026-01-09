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


def is_known_country(country: Optional[str], controlled=None, **kwargs) -> bool:
    """
    Check if a country code is known/valid.
    
    Args:
        country: Country code or name to check
        controlled: Optional set/list of allowed country codes. If provided,
                   country must be in this set. If None, checks against KNOWN_COUNTRIES.
        **kwargs: Accept additional kwargs for compatibility with varying call sites.
    
    Returns:
        True if country is valid (and in controlled set if provided)
    """
    if not country:
        return False
    
    normalized = normalize_country_code(country)
    if normalized is None:
        return False
    
    # If controlled set provided, check against it
    if controlled is not None:
        return normalized in set(controlled)
    
    # Otherwise check against known countries
    return normalized in KNOWN_COUNTRIES
