# ThorTrading/config/symbols.py
from __future__ import annotations
from functools import lru_cache
from typing import List, Optional


@lru_cache(maxsize=256)
def get_active_symbols(country: Optional[str] = None) -> List[str]:
    """Return active symbols (no watchlist filter)."""
    from ThorTrading.models import TradingInstrument

    qs = TradingInstrument.objects.filter(is_active=True)
    if country:
        qs = qs.filter(country=country)

    return list(qs.values_list("symbol", flat=True))


@lru_cache(maxsize=256)
def get_ribbon_symbols(country: Optional[str] = None) -> List[str]:
    """Return active watchlist symbols (used for tracked instruments)."""
    from ThorTrading.models import TradingInstrument

    qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
    if country:
        qs = qs.filter(country=country)

    return list(qs.values_list("symbol", flat=True))


def clear_symbol_caches() -> None:
    """Clear cached symbol lists so admin edits take effect without restart."""
    get_active_symbols.cache_clear()
    get_ribbon_symbols.cache_clear()
