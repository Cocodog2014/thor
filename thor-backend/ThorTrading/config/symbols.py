# ThorTrading/config/symbols.py
from __future__ import annotations
from functools import lru_cache
from typing import List, Optional

@lru_cache(maxsize=256)
def get_active_symbols(country: Optional[str] = None) -> List[str]:
    from ThorTrading.models import TradingInstrument

    qs = TradingInstrument.objects.filter(is_active=True)
    if country:
        qs = qs.filter(country=country)

    return list(qs.values_list("symbol", flat=True))


@lru_cache(maxsize=256)
def get_ribbon_symbols(country: Optional[str] = None) -> List[str]:
    from ThorTrading.models import TradingInstrument

    qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
    if country:
        qs = qs.filter(country=country)

    return list(qs.values_list("symbol", flat=True))
