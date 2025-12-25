from __future__ import annotations
"""Per-quote derived metrics used by quote enrichment."""

from typing import Optional, Dict, Any


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            v = val.strip()
            if v in ("", "—", "NaN", "None", "null"):
                return None
            return float(v)
        return float(val)
    except (ValueError, TypeError):
        return None


def _diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


def _pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return (numerator / denominator) * 100.0


def compute_row_metrics(row: Dict[str, Any]) -> Dict[str, Optional[float]]:
    last = _to_float(row.get("price") or row.get("last"))
    open_price = _to_float(row.get("open_price"))
    prev_close = _to_float(row.get("previous_close"))
    high = _to_float(row.get("high_price"))
    low = _to_float(row.get("low_price"))
    bid = _to_float(row.get("bid"))
    ask = _to_float(row.get("ask"))

    last_prev_diff = _diff(last, prev_close)
    open_prev_diff = _diff(open_price, prev_close)
    high_prev_diff = _diff(high, prev_close)
    low_prev_diff = _diff(low, prev_close)
    range_diff = _diff(high, low)
    spread = _diff(ask, bid)

    ext = row.get("extended_data", {}) or {}
    high_52w = _to_float(ext.get("high_52w") or row.get("high_52w"))
    low_52w = _to_float(ext.get("low_52w") or row.get("low_52w"))

    last_above_low_52w_diff = _diff(last, low_52w)
    last_above_low_52w_pct = _pct(last_above_low_52w_diff, low_52w)

    last_below_high_52w_diff = _diff(high_52w, last)
    last_below_high_52w_pct = _pct(last_below_high_52w_diff, high_52w)

    return {
        "last_prev_diff": last_prev_diff,
        "last_prev_pct": _pct(last_prev_diff, prev_close),
        "open_prev_diff": open_prev_diff,
        "open_prev_pct": _pct(open_prev_diff, prev_close),
        "high_prev_diff": high_prev_diff,
        "high_prev_pct": _pct(high_prev_diff, prev_close),
        "low_prev_diff": low_prev_diff,
        "low_prev_pct": _pct(low_prev_diff, prev_close),
        "range_diff": range_diff,
        "range_pct": _pct(range_diff, prev_close),
        "spread": spread,
        "last_52w_above_low_diff": last_above_low_52w_diff,
        "last_52w_above_low_pct": last_above_low_52w_pct,
        "last_52w_below_high_diff": last_below_high_52w_diff,
        "last_52w_below_high_pct": last_below_high_52w_pct,
    }


__all__ = ["compute_row_metrics"]
