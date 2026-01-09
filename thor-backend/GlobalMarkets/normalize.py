"""
Import-safe normalization utilities.
NO ORM imports here.
"""

from typing import Optional

def normalize_country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None
    code = str(country).upper().strip()
    return code or None
