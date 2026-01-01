from __future__ import annotations

from decimal import Decimal as D


def safe_decimal(val):
    """Convert input to Decimal or return None."""

    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except Exception:
        return None
