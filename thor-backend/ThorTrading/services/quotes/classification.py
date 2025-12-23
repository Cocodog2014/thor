"""Classification & weighting logic for futures instruments.

Centralizes the translation of net change into:
- Signal (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)
- Stat value for composite
- Contract weight and signal weight

Design goals:
1. Keep live data providers focused on raw data only.
2. Keep models light.
3. Allow DB-driven thresholds/weights.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Optional, Tuple

from ThorTrading.models import SignalStatValue, ContractWeight, SignalWeight
from ThorTrading.constants import SYMBOL_NORMALIZE_MAP


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


def _normalize_symbol(symbol: str) -> str:
    base = symbol.lstrip('/')
    return SYMBOL_NORMALIZE_MAP.get(base, base)


@lru_cache(maxsize=256)
def _get_stat_map_for_symbol(symbol: str) -> dict:
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
    normalized = _normalize_symbol(symbol)
    try:
        cw = ContractWeight.objects.get(instrument__symbol__in=[normalized, f'/{normalized}'])
        return Decimal(cw.weight)
    except ContractWeight.DoesNotExist:
        return Decimal('1')


@lru_cache(maxsize=32)
def _get_signal_weight(signal: str) -> int:
    try:
        sw = SignalWeight.objects.get(signal=signal)
        return sw.weight
    except SignalWeight.DoesNotExist:
        return 0


def _is_bear_market_instrument(symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)
    return normalized in {'VX', 'DX', 'GC', 'ZB'}


def _get_inverted_signal_weight(signal: str) -> int:
    weight_map = {
        'STRONG_BUY': -2,
        'BUY': -1,
        'HOLD': 0,
        'SELL': 1,
        'STRONG_SELL': 2,
    }
    return weight_map.get(signal, 0)


def classify(symbol: str, net_change: Optional[Decimal | float | str]) -> Tuple[Optional[str], Optional[Decimal], Decimal, int]:
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

    strong_buy = stat_map.get('STRONG_BUY')
    buy = stat_map.get('BUY')
    sell = stat_map.get('SELL')
    strong_sell = stat_map.get('STRONG_SELL')

    if None in (strong_buy, buy, sell, strong_sell):
        return None, None, contract_weight, 0

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

    if _is_bear_market_instrument(symbol):
        signal_weight = _get_inverted_signal_weight(signal)
    else:
        signal_weight = _get_signal_weight(signal)

    return signal, stat_value, contract_weight, signal_weight


def enrich_quote_row(row: dict) -> dict:
    instrument = row.get('instrument', {})
    symbol = instrument.get('symbol') or ''
    extended = row.setdefault('extended_data', {})

    if not extended.get('signal'):
        change_raw = row.get('change')
        signal, stat_value, contract_weight, signal_weight = classify(symbol, change_raw)
        if signal:
            extended['signal'] = signal
        if stat_value is not None:
            extended['stat_value'] = str(stat_value)
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(contract_weight)
        extended['signal_weight'] = str(signal_weight)
    else:
        if 'contract_weight' not in extended:
            extended['contract_weight'] = str(_get_weight_for_symbol(symbol))
        if 'signal_weight' not in extended:
            existing_signal = extended.get('signal')
            extended['signal_weight'] = str(_get_signal_weight(existing_signal)) if existing_signal else '0'
    return row


def compute_composite(rows: list[dict]) -> dict:
    if not rows:
        return {
            'sum_weighted': '0.00',
            'avg_weighted': None,
            'count': 0,
            'denominator': '0.00',
            'as_of': None,
            'signal_weight_sum': 0,
            'composite_signal': None,
            'composite_signal_weight': 0,
        }

    def _identity(row: dict) -> tuple:
        inst = row.get('instrument', {})
        return (
            inst.get('country'),
            inst.get('future') or inst.get('symbol'),
            row.get('capture_group') or inst.get('capture_group'),
        )

    target_identity = _identity(rows[0])
    filtered_rows = [r for r in rows if _identity(r) == target_identity]
    filtered_rows.sort(key=lambda r: r.get('timestamp') or '', reverse=True)

    sum_weighted = Decimal('0')
    denom = Decimal('0')
    signal_weight_sum = 0

    for r in filtered_rows:
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
    as_of = filtered_rows[0].get('timestamp') if filtered_rows else None

    composite_signal = None
    composite_signal_weight = 0

    if signal_weight_sum > 9:
        composite_signal = "STRONG_BUY"
        composite_signal_weight = 2
    elif 3 < signal_weight_sum <= 9:
        composite_signal = "BUY"
        composite_signal_weight = 1
    elif -3 <= signal_weight_sum <= 3:
        composite_signal = "HOLD"
        composite_signal_weight = 0
    elif -9 <= signal_weight_sum < -3:
        composite_signal = "SELL"
        composite_signal_weight = -1
    elif signal_weight_sum < -9:
        composite_signal = "STRONG_SELL"
        composite_signal_weight = -2

    return {
        'sum_weighted': str(sum_weighted.quantize(Decimal('0.01'))),
        'avg_weighted': str(avg.quantize(Decimal('0.001'))) if avg is not None else None,
        'count': len(filtered_rows),
        'denominator': str(denom.quantize(Decimal('0.01'))),
        'as_of': as_of,
        'signal_weight_sum': signal_weight_sum,
        'composite_signal': composite_signal,
        'composite_signal_weight': composite_signal_weight,
    }


__all__ = [
    'classify', 'enrich_quote_row', 'compute_composite'
]
