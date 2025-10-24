from typing import Optional, Dict, Any


def _to_float(val: Any) -> Optional[float]:
    """Best-effort float conversion. Returns None for null/blank/non-numeric."""
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
    """
    Compute derived metrics for a single market data row.

    Expected row fields (string/number/None):
      - price (aka last), open_price, previous_close, high_price, low_price, bid, ask

    Returns numeric fields (or None):
      - last_prev_diff, last_prev_pct
      - open_prev_diff, open_prev_pct
      - high_prev_diff, high_prev_pct
      - low_prev_diff, low_prev_pct
      - range_diff, range_pct
      - spread
    """
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
    }
