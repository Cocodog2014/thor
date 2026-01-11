from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping


try:  # Keep contracts importable even if LiveData isn't installed/available.
    from LiveData.shared.redis_client import live_data_redis
except Exception:  # pragma: no cover
    live_data_redis = None  # type: ignore


_DECIMAL_FIELDS = ("last", "mark", "mid", "bid", "ask", "close")


def _to_decimal(value) -> Decimal | None:
    if value in (None, "", "None"):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _pick_price(quote: Mapping) -> Decimal | None:
    for key in _DECIMAL_FIELDS:
        if key in quote:
            d = _to_decimal(quote.get(key))
            if d is not None:
                return d
    return None


def get_mark(symbol: str) -> Decimal | None:
    """Return a best-effort mark/last price for `symbol` from Redis."""

    if live_data_redis is None:
        return None

    getter = getattr(live_data_redis, "get_latest_quote", None)
    if not callable(getter):
        return None

    quote = getter((symbol or "").upper())
    if not quote:
        return None

    if isinstance(quote, dict):
        return _pick_price(quote)

    # Some quote providers might return JSON strings/objects; keep it simple here.
    return None


def get_marks(symbols: Iterable[str]) -> dict[str, Decimal | None]:
    """Vectorized version of `get_mark` (no pipelining required yet)."""

    result: dict[str, Decimal | None] = {}
    for symbol in symbols:
        sym = (symbol or "").upper()
        if not sym:
            continue
        result[sym] = get_mark(sym)
    return result


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    mark: Decimal | None


def get_quote_snapshot(symbol: str) -> QuoteSnapshot:
    """Convenience wrapper for callers that want a structured payload."""

    sym = (symbol or "").upper()
    return QuoteSnapshot(symbol=sym, mark=get_mark(sym))
