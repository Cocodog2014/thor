# ThorTrading/config/markets.py
from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence

from GlobalMarkets.models.market import Market
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


def _country(m: Market) -> Optional[str]:
    raw = getattr(m, "country", None)
    return (normalize_country_code(raw) or raw) if raw else None


def _tz_sort_key(m: Market) -> tuple:
    """
    Try to sort markets east->west using whatever timezone info exists on Market.
    Falls back safely if those fields don't exist.
    """
    # Common field names you *might* have:
    # - utc_offset_minutes (e.g., +540 for Japan, -300 for NY)
    # - utc_offset (hours)
    # - timezone (IANA string like 'Asia/Tokyo')  -> can't sort without parsing
    # We'll try a few and fall back.

    # 1) minutes offset field
    off_min = getattr(m, "utc_offset_minutes", None)
    if isinstance(off_min, int):
        # East (positive) first, West (negative) later -> sort by descending
        return (-off_min, _country(m) or "")

    # 2) hours offset field
    off_hr = getattr(m, "utc_offset", None)
    if isinstance(off_hr, (int, float)):
        return (-(float(off_hr) * 60.0), _country(m) or "")

    # 3) unknown fields -> alphabetical stable
    return (0, _country(m) or "")


def get_control_markets(
    *,
    require_session_capture: bool = False,
) -> List[Market]:
    """
    Source of truth for 'controlled markets' is GlobalMarkets DB.

    - is_active=True always
    - optionally require enable_session_capture=True
      (turn this on if you ONLY want markets that run the session pipeline)
    """
    qs = Market.objects.filter(is_active=True)
    if require_session_capture:
        qs = qs.filter(enable_session_capture=True)

    markets = list(qs)
    # sort east->west if possible, else stable fallback
    markets.sort(key=_tz_sort_key)
    return markets


def get_control_countries(*, require_session_capture: bool = False) -> List[str]:
    """
    Returns a list of controlled country codes (normalized), ordered.
    """
    countries: List[str] = []
    for m in get_control_markets(require_session_capture=require_session_capture):
        c = _country(m)
        if c:
            countries.append(c)

    # de-dupe while preserving order
    seen = set()
    ordered = []
    for c in countries:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered
