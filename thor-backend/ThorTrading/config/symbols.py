# ThorTrading/config/symbols.py
from __future__ import annotations
from functools import lru_cache
from typing import Dict, List, Optional

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


def clear_symbol_caches() -> None:
    """Clear cached symbol lists so admin edits take effect without restart."""
    get_active_symbols.cache_clear()
    get_ribbon_symbols.cache_clear()
    # Refresh module-level constants to keep legacy callers in sync
    FUTURES_SYMBOLS.clear()
    FUTURES_SYMBOLS.extend(_load_symbols())
    REDIS_SYMBOL_MAP.clear()
    REDIS_SYMBOL_MAP.update({sym: sym for sym in FUTURES_SYMBOLS})
    SYMBOL_NORMALIZE_MAP.clear()
    SYMBOL_NORMALIZE_MAP.update({sym: sym for sym in FUTURES_SYMBOLS})


def _load_symbols() -> List[str]:
    try:
        return get_active_symbols()
    except Exception:
        return []


# Backwards-compatible constants (now DB-driven; refreshed via clear_symbol_caches + manual reload)
FUTURES_SYMBOLS: List[str] = _load_symbols()
REDIS_SYMBOL_MAP: Dict[str, str] = {sym: sym for sym in FUTURES_SYMBOLS}
SYMBOL_NORMALIZE_MAP: Dict[str, str] = {sym: sym for sym in FUTURES_SYMBOLS}
