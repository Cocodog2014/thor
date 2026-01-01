from __future__ import annotations

"""Utilities for the intraday supervisor engine."""

from decimal import Decimal as D


def safe_decimal(val):
    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except Exception:
        return None
