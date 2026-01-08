"""
Compatibility shim for legacy imports:

    from GlobalMarkets.services.market_clock import is_market_open_now

New truth lives in GlobalMarkets/services.py (or wherever your compute_market_status is).
This shim provides the old function names using the new 3-model system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.services import compute_market_status  # <-- this is YOUR new engine


def is_market_open_now(market: Market, *, now_utc: Optional[datetime] = None) -> bool:
    now_utc = now_utc or timezone.now()
    computed = compute_market_status(market, now_utc=now_utc)
    return bool(computed and computed.status == Market.Status.OPEN)


def is_market_closed_now(market: Market, *, now_utc: Optional[datetime] = None) -> bool:
    now_utc = now_utc or timezone.now()
    computed = compute_market_status(market, now_utc=now_utc)
    return bool(computed and computed.status == Market.Status.CLOSED)


def is_market_premarket_now(market: Market, *, now_utc: Optional[datetime] = None) -> bool:
    now_utc = now_utc or timezone.now()
    computed = compute_market_status(market, now_utc=now_utc)
    return bool(computed and computed.status == Market.Status.PREMARKET)
