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
  * signal_key is one of SIGNAL_CHOICES keys (or None)
  * stat_value is Decimal or None
  * weight is Decimal (defaults to 1)
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Optional, Tuple

from ..models import SignalStatValue, ContractWeight, SignalWeight
from FutureTrading.constants import SYMBOL_NORMALIZE_MAP

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
    'VX': {'STRONG_BUY': Decimal('0.05'), 'BUY': Decimal('0.03'), 'HOLD': Decimal('0'), 'SELL': Decimal('-0.03'), 'STRONG_SELL': Decimal('-0.05')},
    'DX': {'STRONG_BUY': Decimal('30'), 'BUY': Decimal('5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-5'), 'STRONG_SELL': Decimal('-30')},
    'ZB': {'STRONG_BUY': Decimal('30'), 'BUY': Decimal('5'), 'HOLD': Decimal('0'), 'SELL': Decimal('-5'), 'STRONG_SELL': Decimal('-30')},
}

SIGNAL_ORDER = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']

# Symbol aliases - maps Excel/TOS symbols to database symbols
 # Deprecated legacy alias map replaced by SYMBOL_NORMALIZE_MAP
SYMBOL_ALIASES = SYMBOL_NORMALIZE_MAP


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol, handling aliases and slashes.
    
    Returns the canonical symbol without leading slash.
    """
    base = symbol.lstrip('/')
    return SYMBOL_ALIASES.get(base, base)


@lru_cache(maxsize=256)
def _get_stat_map_for_symbol(symbol: str) -> dict:
    """Fetch stat values for a symbol from DB, fallback to static map.

    Accepts symbols with or without leading slash ("/YM" vs "YM").
    Handles symbol aliases (e.g., "RT" -> "RTY").
    """
    normalized = _normalize_symbol(symbol)
    qs = SignalStatValue.objects.filter(instrument__symbol__in=[normalized, f'/{normalized}'])
    if not qs.exists():
        return FALLBACK_STAT_MAP.get(normalized, {})
    out = {}
    for row in qs:
        out[row.signal] = Decimal(row.value)
    return out


@lru_cache(maxsize=256)
def _get_weight_for_symbol(symbol: str) -> Decimal:
    """Fetch contract weight from DB or return Decimal('1').
    
    Handles symbol aliases (e.g., "RT" -> "RTY").
    """
    normalized = _normalize_symbol(symbol)
    try:
        cw = ContractWeight.objects.get(instrument__symbol__in=[normalized, f'/{normalized}'])
        return Decimal(cw.weight)
    except ContractWeight.DoesNotExist:
        return Decimal('1')


@lru_cache(maxsize=32)
def _get_signal_weight(signal: str) -> int:
    """Fetch signal weight from DB (2, 1, 0, -1, -2) or return 0."""
    try:
        sw = SignalWeight.objects.get(signal=signal)
        return sw.weight
    except SignalWeight.DoesNotExist:
        return 0


def _is_bear_market_instrument(symbol: str) -> bool:
    """Check if symbol is a bear market instrument with inverted logic.
    
    Bear market instruments (safety/insurance assets):
    - VX: VIX - volatility index (fear gauge)
    - DX: Dollar Index - safe haven currency
    - GC: Gold - safe haven metal
    - ZB: 30-Year Treasury Bond - safe haven bond (flight to safety)
    
    When these go UP, it's typically bearish for stocks (people fleeing to safety).
    So we invert their signal weights for the composite calculation.
    
    Handles symbol aliases (e.g., "RT" -> "RTY").
    """
    normalized = _normalize_symbol(symbol)
    return normalized in {'VX', 'DX', 'GC', 'ZB'}


def _get_inverted_signal_weight(signal: str) -> int:
    """Get inverted signal weight for bear market instruments."""
    # For bear market instruments, invert the weight:
    # STRONG_BUY (market up) -> -2 (bearish for stocks)
    # BUY (market up) -> -1 (bearish for stocks)  
    # HOLD -> 0
    # SELL (market down) -> +1 (bullish for stocks)
    # STRONG_SELL (market down) -> +2 (bullish for stocks)
    weight_map = {
        'STRONG_BUY': -2,
        'BUY': -1,
        'HOLD': 0,
        'SELL': 1,
        'STRONG_SELL': 2,
    }
    return weight_map.get(signal, 0)


def classify(symbol: str, net_change: Optional[Decimal | float | str]) -> Tuple[Optional[str], Optional[Decimal], Decimal, int]:
    """Classify a net change into a signal, returning (signal, stat_value, contract_weight, signal_weight).

    If net_change is None or cannot be parsed, returns (None, None, contract_weight, 0).
    """
    contract_weight = _get_weight_for_symbol(symbol)
    if net_change is None:
        return None, None, contract_weight, 0

    try:
        change = Decimal(str(net_change))
    except Exception:
        return None, None, contract_weight, 0

    stat_map = _get_stat_map_for_symbol(symbol)
    if not stat_map:
        return None, None, contract_weight, 0

    # Extract needed values with fallbacks
    strong_buy = stat_map.get('STRONG_BUY')
    buy = stat_map.get('BUY')
    sell = stat_map.get('SELL')
    strong_sell = stat_map.get('STRONG_SELL')

    if None in (strong_buy, buy, sell, strong_sell):  # incomplete data
        return None, None, contract_weight, 0

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
    
    # Use inverted weights for bear market instruments
    if _is_bear_market_instrument(symbol):
        signal_weight = _get_inverted_signal_weight(signal)
    else:
        signal_weight = _get_signal_weight(signal)
        
    return signal, stat_value, contract_weight, signal_weight


def enrich_quote_row(row: dict) -> dict:
    """Given a single quote dict (instrument + fields) add signal/stat/weights if missing.

    Mutates and returns the row for convenience.
    Expected structure matches what LatestQuotesView assembles before enrichment.
    """
    instrument = row.get('instrument', {})
    symbol = instrument.get('symbol') or ''
    extended = row.setdefault('extended_data', {})

    # Only classify if we do not already have a signal
    if not extended.get('signal'):
        change_raw = row.get('change')
        signal, stat_value, contract_weight, signal_weight = classify(symbol, change_raw)
        if signal:
            extended['signal'] = signal
        if stat_value is not None:
            extended['stat_value'] = str(stat_value)
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(contract_weight)
        # Add the signal weight (2, 1, 0, -1, -2) for display in header
        extended['signal_weight'] = str(signal_weight)
    else:
        # Ensure weights present even if signal existed
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(_get_weight_for_symbol(symbol))
        if 'signal_weight' not in extended:
            # Get signal weight based on existing signal
            existing_signal = extended.get('signal')
            if existing_signal:
                extended['signal_weight'] = str(_get_signal_weight(existing_signal))
            else:
                extended['signal_weight'] = '0'
    return row


def compute_composite(rows: list[dict]) -> dict:
    """Compute weighted composite from enriched rows.

    Returns dict with sum_weighted, avg_weighted, count, denominator, as_of, composite_signal, composite_signal_weight.
    """
    sum_weighted = Decimal('0')
    denom = Decimal('0')
    
    # Calculate weighted sum using signal_weight (not stat_value) for composite signal classification
    signal_weight_sum = 0
    
    for r in rows:
        ext = r.get('extended_data', {})
        try:
            v = Decimal(str(ext.get('stat_value')))
            w = Decimal(str(ext.get('contract_weight', '1')))
            signal_weight = int(ext.get('signal_weight', 0))
        except Exception:
            continue
        
        sum_weighted += v * w
        denom += abs(w)
        signal_weight_sum += signal_weight

    avg = (sum_weighted / denom) if denom > 0 else None
    as_of = rows[0].get('timestamp') if rows else None
    
    # VBA Composite Signal Classification Logic
    # TotalBuyV = 9, TotalHoldHighV = 3, TotalHoldLowV = -3, TotalSellV = -9
    composite_signal = None
    composite_signal_weight = 0
    
    if signal_weight_sum > 9:  # Strong Buy
        composite_signal = "STRONG_BUY"
        composite_signal_weight = 2
    elif signal_weight_sum > 3 and signal_weight_sum <= 9:  # Buy
        composite_signal = "BUY" 
        composite_signal_weight = 1
    elif signal_weight_sum >= -3 and signal_weight_sum <= 3:  # Hold
        composite_signal = "HOLD"
        composite_signal_weight = 0
    elif signal_weight_sum < -3 and signal_weight_sum >= -9:  # Sell
        composite_signal = "SELL"
        composite_signal_weight = -1
    elif signal_weight_sum < -9:  # Strong Sell
        composite_signal = "STRONG_SELL"
        composite_signal_weight = -2
    
    return {
        'sum_weighted': str(sum_weighted.quantize(Decimal('0.01'))),
        'avg_weighted': str(avg.quantize(Decimal('0.001'))) if avg is not None else None,
        'count': len(rows),
        'denominator': str(denom.quantize(Decimal('0.01'))),
        'as_of': as_of,
        'signal_weight_sum': signal_weight_sum,
        'composite_signal': composite_signal,
        'composite_signal_weight': composite_signal_weight,
    }


__all__ = [
    'classify', 'enrich_quote_row', 'compute_composite'
]
