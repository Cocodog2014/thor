"""Classification & weighting logic for futures instruments.

This module centralizes the translation of a net change value into a
human-readable signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL) and the
corresponding statistical value used for the composite weighted average.

Design goals:
1. Keep SchwabLiveData (and other providers) focused solely on *raw* live data.
2. Keep models light (no heavy business logic inside model methods).
3. Allow future replacement of hard‑coded thresholds with DB records.

Current data sources:
* SignalStatValue table already stores per-instrument numeric values for each
  signal state (e.g. YM STRONG_BUY=60, BUY=10, HOLD=0, SELL=-10, STRONG_SELL=-60).
  We leverage those to both (a) return the stat_value when a signal is chosen
  and (b) derive classification thresholds without duplicating constants.
* ContractWeight table supplies the per-instrument weighting used in the
  composite calculation.

Classification logic (derived from VBA snippet):

Given the net change (points) for an instrument and its configured
SignalStatValue numbers:

Let:
  S_BUY  = value for STRONG_BUY  (largest positive)
  BUY    = value for BUY         (smaller positive)
  HOLD   = 0 (or configured)
  SELL   = value for SELL        (negative small)
  S_SELL = value for STRONG_SELL (negative large)

Then:
  if change >  S_BUY      -> STRONG_BUY
  elif change > BUY       -> BUY
  elif change >= SELL     -> HOLD          (i.e. within [-|SELL|, BUY])
  elif change >  S_SELL   -> SELL
  else                    -> STRONG_SELL

Edge cases:
  * Missing change => returns None (no classification)
  * Missing stat values in DB => falls back to default map below

The function returns a tuple (signal_key, stat_value, weight) where:
  * signal_key is one of TradingSignal.SIGNAL_CHOICES keys (or None)
  * stat_value is Decimal or None
  * weight is Decimal (defaults to 1)
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Optional, Tuple

from ..models import SignalStatValue, ContractWeight, TradingInstrument

# Fallback static defaults (only used if DB rows missing) – mirrors management command
FALLBACK_STAT_MAP = {
    'YM': {'STRONG_BUY': Decimal('60'), 'BUY': Decimal('10'), 'HOLD': Decimal('0'), 'SELL': Decimal('-10'), 'STRONG_SELL': Decimal('-60')},
    'ES': {'STRONG_BUY': Decimal('6'), 'BUY': Decimal('1'), 'HOLD': Decimal('0'), 'SELL': Decimal('-1'), 'STRONG_SELL': Decimal('-6')},
    'NQ': {'STRONG_BUY': Decimal('15'), 'BUY': Decimal('2.5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-2.5'), 'STRONG_SELL': Decimal('-15')},
    'RTY': {'STRONG_BUY': Decimal('15'), 'BUY': Decimal('2.5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-2.5'), 'STRONG_SELL': Decimal('-15')},
    'CL': {'STRONG_BUY': Decimal('0.3'), 'BUY': Decimal('0.05'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.05'), 'STRONG_SELL': Decimal('-0.3')},
    'SI': {'STRONG_BUY': Decimal('0.06'), 'BUY': Decimal('0.01'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.01'), 'STRONG_SELL': Decimal('-0.06')},
    'HG': {'STRONG_BUY': Decimal('0.012'), 'BUY': Decimal('0.002'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.002'), 'STRONG_SELL': Decimal('-0.012')},
    'GC': {'STRONG_BUY': Decimal('3'), 'BUY': Decimal('0.5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.5'), 'STRONG_SELL': Decimal('-3')},
    'VX': {'STRONG_BUY': Decimal('0.10'), 'BUY': Decimal('0.05'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.05'), 'STRONG_SELL': Decimal('-0.10')},
    'DX': {'STRONG_BUY': Decimal('30'), 'BUY': Decimal('5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-5'), 'STRONG_SELL': Decimal('-30')},
    'ZB': {'STRONG_BUY': Decimal('30'), 'BUY': Decimal('5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-5'), 'STRONG_SELL': Decimal('-30')},
}

SIGNAL_ORDER = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']


@lru_cache(maxsize=256)
def _get_stat_map_for_symbol(symbol: str) -> dict:
    """Fetch stat values for a symbol from DB, fallback to static map.

    Accepts symbols with or without leading slash ("/YM" vs "YM").
    """
    base = symbol.lstrip('/')
    qs = SignalStatValue.objects.filter(instrument__symbol__in=[base, f'/{base}'])
    if not qs.exists():
        return FALLBACK_STAT_MAP.get(base, {})
    out = {}
    for row in qs:
        out[row.signal] = Decimal(row.value)
    return out


@lru_cache(maxsize=256)
def _get_weight_for_symbol(symbol: str) -> Decimal:
    """Fetch contract weight from DB or return Decimal('1')."""
    base = symbol.lstrip('/')
    try:
        cw = ContractWeight.objects.get(instrument__symbol__in=[base, f'/{base}'])
        return Decimal(cw.weight)
    except ContractWeight.DoesNotExist:
        return Decimal('1')


def classify(symbol: str, net_change: Optional[Decimal | float | str]) -> Tuple[Optional[str], Optional[Decimal], Decimal]:
    """Classify a net change into a signal, returning (signal, stat_value, weight).

    If net_change is None or cannot be parsed, returns (None, None, weight).
    """
    weight = _get_weight_for_symbol(symbol)
    if net_change is None:
        return None, None, weight

    try:
        change = Decimal(str(net_change))
    except Exception:
        return None, None, weight

    stat_map = _get_stat_map_for_symbol(symbol)
    if not stat_map:
        return None, None, weight

    # Extract needed values with fallbacks
    strong_buy = stat_map.get('STRONG_BUY')
    buy = stat_map.get('BUY')
    sell = stat_map.get('SELL')
    strong_sell = stat_map.get('STRONG_SELL')

    if None in (strong_buy, buy, sell, strong_sell):  # incomplete data
        return None, None, weight

    # Classification using inequality ladder (mirrors VBA intent)
    if change > strong_buy:
        signal = 'STRONG_BUY'
    elif change > buy:
        signal = 'BUY'
    elif change >= sell:
        signal = 'HOLD'
    elif change > strong_sell:
        signal = 'SELL'
    else:
        signal = 'STRONG_SELL'

    stat_value = stat_map.get(signal)
    return signal, stat_value, weight


def enrich_quote_row(row: dict) -> dict:
    """Given a single quote dict (instrument + fields) add signal/stat/weight if missing.

    Mutates and returns the row for convenience.
    Expected structure matches what LatestQuotesView assembles before enrichment.
    """
    instrument = row.get('instrument', {})
    symbol = instrument.get('symbol') or ''
    extended = row.setdefault('extended_data', {})

    # Only classify if we do not already have a signal
    if not extended.get('signal'):
        change_raw = row.get('change')
        signal, stat_value, weight = classify(symbol, change_raw)
        if signal:
            extended['signal'] = signal
        if stat_value is not None:
            extended['stat_value'] = str(stat_value)
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(weight)
    else:
        # Ensure weight present even if signal existed
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(_get_weight_for_symbol(symbol))
    return row


def compute_composite(rows: list[dict]) -> dict:
    """Compute weighted composite from enriched rows.

    Returns dict with sum_weighted, avg_weighted, count, denominator, as_of.
    """
    sum_weighted = Decimal('0')
    denom = Decimal('0')
    for r in rows:
        ext = r.get('extended_data', {})
        try:
            v = Decimal(str(ext.get('stat_value')))
            w = Decimal(str(ext.get('contract_weight', '1')))
        except Exception:
            continue
        sum_weighted += v * w
        denom += abs(w)

    avg = (sum_weighted / denom) if denom > 0 else None
    as_of = rows[0].get('timestamp') if rows else None
    return {
        'sum_weighted': str(sum_weighted.quantize(Decimal('0.01'))),
        'avg_weighted': str(avg.quantize(Decimal('0.001'))) if avg is not None else None,
        'count': len(rows),
        'denominator': str(denom.quantize(Decimal('0.01'))),
        'as_of': as_of,
    }


__all__ = [
    'classify', 'enrich_quote_row', 'compute_composite'
]
