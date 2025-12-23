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

from typing import List, Dict, Tuple
from decimal import Decimal
import logging

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.constants import CONTROL_COUNTRIES, FUTURES_SYMBOLS, REDIS_SYMBOL_MAP, SYMBOL_NORMALIZE_MAP
from ThorTrading.models.extremes import Rolling52WeekStats
from ThorTrading.models import TradingInstrument
from ThorTrading.services.classification import enrich_quote_row, compute_composite
from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES
from ThorTrading.services.country_codes import normalize_country_code, is_known_country
from ThorTrading.services.metrics import compute_row_metrics

logger = logging.getLogger(__name__)


def _fallback_country_from_clock() -> str | None:
    """Best-effort country assignment when quotes lack country.

    Uses the currently open control market (if any), ordered by CONTROL_COUNTRIES
    to provide a deterministic fallback.
    """
    try:
        from GlobalMarkets.models.market import Market

        markets = list(Market.objects.filter(is_active=True, is_control_market=True))
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

    order = {normalize_country_code(c) or c: idx for idx, c in enumerate(CONTROL_COUNTRIES)}

    def _rank(market):
        key = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
        return order.get(key, len(order))

    candidates.sort(key=_rank)
    chosen = candidates[0]
    return normalize_country_code(getattr(chosen, "country", None)) or getattr(chosen, "country", None)


def fetch_raw_quotes() -> Dict[str, Dict]:
    """Fetch latest raw quotes from Redis for all tracked futures symbols."""
    out: Dict[str, Dict] = {}
    for sym in FUTURES_SYMBOLS:
        key = REDIS_SYMBOL_MAP.get(sym, sym)
        try:
            data = live_data_redis.get_latest_quote(key)
            if data:
                out[sym] = data
        except Exception as e:
            logger.error(f"Redis fetch failed for {sym}: {e}")
    return out


def _to_str(v):
    return str(v) if v is not None else None


def build_enriched_rows(raw_quotes: Dict[str, Dict]) -> List[Dict]:
    """Return enriched row dicts (one per future)."""
    stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}
    # Prefetch display precision for all tracked symbols in one query
    norm_symbols = [SYMBOL_NORMALIZE_MAP.get(sym, sym) for sym in FUTURES_SYMBOLS]
    query_symbols = norm_symbols + [f'/{s}' for s in norm_symbols]
    precision_map: Dict[str, int] = {}
    instrument_meta: Dict[str, Dict[str, str]] = {}
    for inst in TradingInstrument.objects.filter(symbol__in=query_symbols):
        key = inst.symbol.lstrip('/').upper()
        # Prefer first occurrence (avoid overwriting with alt symbol formatting)
        if key not in precision_map:
            precision_map[key] = inst.display_precision
        # Capture tick_value and margin_requirement (convert to str for JSON)
        instrument_meta[key] = {
            'tick_value': _to_str(inst.tick_value),
            'margin_requirement': _to_str(inst.margin_requirement),
        }
    rows: List[Dict] = []
    fallback_country = _fallback_country_from_clock()

    for idx, sym in enumerate(FUTURES_SYMBOLS):
        quote = raw_quotes.get(sym)
        if not quote:
            continue
        norm = SYMBOL_NORMALIZE_MAP.get(sym, sym)
        stat = stats_52w.get(norm)

        raw_country = quote.get('country') or quote.get('market')
        row_country = normalize_country_code(raw_country) or fallback_country
        if not row_country:
            logger.error("Dropping quote for %s missing country: %s", sym, quote)
            continue
        if not is_known_country(row_country, controlled=set(ALLOWED_CONTROL_COUNTRIES)):
            logger.error("Dropping quote for %s with unknown country '%s': %s", sym, row_country, quote)
            continue
        quote['country'] = row_country

        meta = instrument_meta.get(norm, {})
        row = {
            'instrument': {
                'id': idx + 1,
                'symbol': norm,
                'name': norm,
                'exchange': 'TOS',
                'currency': 'USD',
                'display_precision': precision_map.get(norm, 2),
                'is_active': True,
                'sort_order': idx,
                'tick_value': meta.get('tick_value'),
                'margin_requirement': meta.get('margin_requirement'),
                'country': row_country,
            },
            'country': row_country,
            # Ensure downstream composite has a timestamp
            'timestamp': quote.get('timestamp'),
            'price': _to_str(quote.get('last')),
            'last': _to_str(quote.get('last')),
            'bid': _to_str(quote.get('bid')),
            'ask': _to_str(quote.get('ask')),
            'volume': quote.get('volume'),
            'open_price': _to_str(quote.get('open')),
            'high_price': _to_str(quote.get('high')),
            'low_price': _to_str(quote.get('low')),
            'close_price': _to_str(quote.get('close')),
            'previous_close': _to_str(quote.get('close')),
            'change': _to_str(quote.get('change')),
            'change_percent': None,
            'bid_size': quote.get('bid_size'),
            'ask_size': quote.get('ask_size'),
            'extended_data': {
                'high_52w': str(stat.high_52w) if (stat and stat.high_52w) else None,
                'low_52w': str(stat.low_52w) if (stat and stat.low_52w) else None,
            },
        }

        enrich_quote_row(row)
        try:
            metrics = compute_row_metrics(row)
            row.update(metrics)
            if row.get('change_percent') in (None, '', ''):
                row['change_percent'] = metrics.get('last_prev_pct')
        except Exception as e:
            logger.warning(f"Metrics failed for {norm}: {e}")

        rows.append(row)
    return rows


def get_enriched_quotes_with_composite() -> Tuple[List[Dict], Dict]:
    """Convenience helper returning enriched rows + composite summary."""
    raw = fetch_raw_quotes()
    rows = build_enriched_rows(raw)
    composite = compute_composite(rows) if rows else {}
    return rows, composite

__all__ = [
    'fetch_raw_quotes',
    'build_enriched_rows',
    'get_enriched_quotes_with_composite',
]

