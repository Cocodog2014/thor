from __future__ import annotations

"""Utilities for the intraday supervisor engine.

This is relocated from `ThorTrading.services.intraday_supervisor.utils` as part of the
ThorTrading intraday restructure.
"""

from decimal import Decimal as D


def safe_decimal(val):
    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except Exception:
        return None
