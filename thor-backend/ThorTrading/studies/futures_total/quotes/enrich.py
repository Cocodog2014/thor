"""Quote enrichment pipeline for ThorTrading.

Single source for:
- Fetching raw quotes from Redis
- Normalizing symbols
- Attaching 52w stats & instrument metadata
- Enriching rows (classification + metrics)
- Computing composite summary

Used by:
- LatestQuotesView (serve enriched JSON)
- MarketOpenCaptureService (persist MarketSession rows)
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Tuple

from LiveData.shared.redis_client import live_data_redis
from GlobalMarkets.config.markets import get_control_countries
from ThorTrading.models import TradingInstrument
from ThorTrading.models.extremes import Rolling52WeekStats
from ThorTrading.services.config.country_codes import is_known_country, normalize_country_code

from .classification import compute_composite, enrich_quote_row
from .row_metrics import compute_row_metrics

logger = logging.getLogger(__name__)


def _load_raw_quote(symbol: str) -> dict | None:
    key = f"raw:quote:{symbol.upper()}"
    raw = live_data_redis.client.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _as_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _fallback_country_from_clock(control_countries: list[str]) -> str | None:
    """Best-effort country assignment when quotes lack country.

    Uses the currently open control market (if any), ordered by control_countries
    to provide a deterministic fallback.
    """
    try:
        from GlobalMarkets.models.market import Market

        markets = list(Market.objects.filter(is_active=True))
    except Exception:
        return None

    if not markets:
        return None

    def _is_open(market) -> bool:
        status = getattr(market, "status", None)
        if status == "OPEN":
            return True
        try:
            info = market.get_market_status()
            if info and (info.get("status") == "OPEN" or info.get("is_open")):
                return True
        except Exception:
            return False
        return False

    open_markets = [m for m in markets if _is_open(m)]
    candidates = open_markets or markets

    order = {normalize_country_code(c) or c: idx for idx, c in enumerate(control_countries)}

    def _rank(market):
        key = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
        return order.get(key, len(order))

    candidates.sort(key=_rank)
    chosen = candidates[0]
    return normalize_country_code(getattr(chosen, "country", None)) or getattr(chosen, "country", None)


def _tracked_instruments() -> List[TradingInstrument]:
    """Return active/watchlist instruments in a stable order."""
    try:
        qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
        instruments = list(qs.order_by("sort_order", "symbol")) if qs.model._meta.get_field("symbol") else list(qs)
        return instruments
    except Exception:
        logger.exception("Failed to load tracked instruments")
        return []


def fetch_raw_quotes() -> Dict[str, Dict]:
    """Fetch latest raw quotes from Redis for all tracked instruments."""
    out: Dict[str, Dict] = {}
    for inst in _tracked_instruments():
        sym = inst.symbol.lstrip("/").upper()
        key = inst.symbol  # use stored symbol as redis key
        try:
            data = live_data_redis.get_latest_quote(key)
            if data:
                out[sym] = data
        except Exception as e:
            logger.error("Redis fetch failed for %s: %s", sym, e)
    return out


def _to_str(v):
    return str(v) if v is not None else None


def build_enriched_rows(raw_quotes: Dict[str, Dict]) -> List[Dict]:
    """Return enriched row dicts (one per tracked instrument)."""
    control_countries = get_control_countries(require_session_capture=True)
    stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}

    instruments = _tracked_instruments()
    rows: List[Dict] = []
    fallback_country = _fallback_country_from_clock(control_countries)

    for idx, inst in enumerate(instruments):
        sym = inst.symbol.lstrip("/").upper()
        quote = raw_quotes.get(sym)
        if not quote:
            continue

        stat = stats_52w.get(sym)

        inst_country = normalize_country_code(getattr(inst, "country", None))
        raw_country = quote.get("country") or quote.get("market")

        # Prefer instrument-level country tagging so cloned instruments remain scoped to their market,
        # falling back to provider country or the control-country clock when missing.
        row_country = inst_country or normalize_country_code(raw_country) or fallback_country
        if not row_country:
            logger.error("Dropping quote for %s missing country: %s", sym, quote)
            continue
        if not is_known_country(row_country, controlled=set(control_countries)):
            logger.error("Dropping quote for %s with unknown country '%s': %s", sym, row_country, quote)
            continue
        quote["country"] = row_country

        row = {
            "instrument": {
                "id": idx + 1,
                "symbol": sym,
                "name": inst.name or sym,
                "exchange": getattr(inst, "exchange", "TOS"),
                "currency": getattr(inst, "currency", "USD"),
                "display_precision": getattr(inst, "display_precision", 2),
                "is_active": getattr(inst, "is_active", True),
                "sort_order": getattr(inst, "sort_order", idx),
                "tick_value": _to_str(getattr(inst, "tick_value", None)),
                "margin_requirement": _to_str(getattr(inst, "margin_requirement", None)),
                "country": row_country,
            },
            "country": row_country,
            "timestamp": quote.get("timestamp"),
            "price": _to_str(quote.get("last")),
            "last": _to_str(quote.get("last")),
            "bid": _to_str(quote.get("bid")),
            "ask": _to_str(quote.get("ask")),
            "volume": quote.get("volume"),
            "open_price": _to_str(quote.get("open")),
            "high_price": _to_str(quote.get("high")),
            "low_price": _to_str(quote.get("low")),
            "close_price": _to_str(quote.get("close")),
            "previous_close": _to_str(quote.get("close")),
            "change": _to_str(quote.get("change")),
            "change_percent": None,
            "bid_size": quote.get("bid_size"),
            "ask_size": quote.get("ask_size"),
            "extended_data": {
                "high_52w": str(stat.high_52w) if (stat and stat.high_52w) else None,
                "low_52w": str(stat.low_52w) if (stat and stat.low_52w) else None,
            },
            "source": "OTHER",
        }

        # Prefer raw Excel quote for price fields when available
        rawq = _load_raw_quote(sym)
        if rawq:
            raw_last = _as_float(rawq.get("last"))
            raw_bid = _as_float(rawq.get("bid"))
            raw_ask = _as_float(rawq.get("ask"))

            if raw_last is not None:
                row["last"] = raw_last
                row["price"] = raw_last
                if raw_bid is not None:
                    row["bid"] = raw_bid
                if raw_ask is not None:
                    row["ask"] = raw_ask
                if rawq.get("volume") is not None:
                    row["volume"] = rawq.get("volume")
                if not row.get("timestamp") and rawq.get("timestamp") is not None:
                    row["timestamp"] = rawq.get("timestamp")
                row["source"] = "TOS_EXCEL"

        enrich_quote_row(row)
        try:
            metrics = compute_row_metrics(row)
            row.update(metrics)
            if row.get("change_percent") in (None, "", ""):
                row["change_percent"] = metrics.get("last_prev_pct")
        except Exception as e:
            logger.warning("Metrics failed for %s: %s", sym, e)

        rows.append(row)
    return rows


def get_enriched_quotes_with_composite() -> Tuple[List[Dict], Dict]:
    """Convenience helper returning enriched rows + composite summary."""
    raw = fetch_raw_quotes()
    rows = build_enriched_rows(raw)
    composite = compute_composite(rows) if rows else {}
    return rows, composite


__all__ = [
    "fetch_raw_quotes",
    "build_enriched_rows",
    "get_enriched_quotes_with_composite",
]
