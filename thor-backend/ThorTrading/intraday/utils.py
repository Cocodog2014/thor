from __future__ import annotations

from decimal import Decimal as D


def safe_decimal(val):
    """Convert input to Decimal or return None.

    This is the canonical `safe_decimal` used by intraday + indicator services.
    """

    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except Exception:
        return None
