"""
Historical backtest statistics for MarketSession rows.

Moved under studies/futures_total because it belongs to that study family.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ThorTrading.models.MarketSession import MarketSession

# Canonical signal/outcome values so callers avoid typos
BHS_STRONG_BUY = "STRONG_BUY"
BHS_BUY = "BUY"
BHS_HOLD = "HOLD"
BHS_SELL = "SELL"
BHS_STRONG_SELL = "STRONG_SELL"

WNDW_WORKED = "WORKED"
WNDW_DIDNT_WORK = "DIDNT_WORK"


def _base_queryset(country: str, symbol: str, as_of: Optional[datetime]):
    qs = MarketSession.objects.filter(country=country, symbol=symbol)
    if as_of is not None:
        qs = qs.filter(captured_at__lt=as_of)
    return qs


def _signal_counts(qs, signal: str):
    signal_qs = qs.filter(bhs=signal)
    worked = signal_qs.filter(wndw=WNDW_WORKED).count()
    didnt = signal_qs.filter(wndw=WNDW_DIDNT_WORK).count()
    trades = worked + didnt

    if trades > 0:
        worked_pct = (worked / trades) * 100.0
        didnt_pct = (didnt / trades) * 100.0
    else:
        worked_pct = 0.0
        didnt_pct = 0.0

    return worked, worked_pct, didnt, didnt_pct


def compute_backtest_stats_for_country_symbol(
    *,
    country: str,
    symbol: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute per-signal historical accuracy for the given (country, symbol)."""

    qs = _base_queryset(country=country, symbol=symbol, as_of=as_of)

    stats: Dict[str, Any] = {}

    sb_w, sb_wp, sb_d, sb_dp = _signal_counts(qs, BHS_STRONG_BUY)
    b_w, b_wp, b_d, b_dp = _signal_counts(qs, BHS_BUY)
    s_w, s_wp, s_d, s_dp = _signal_counts(qs, BHS_SELL)
    ss_w, ss_wp, ss_d, ss_dp = _signal_counts(qs, BHS_STRONG_SELL)
    hold_count = qs.filter(bhs=BHS_HOLD).count()

    stats.update(
        strong_buy_worked=sb_w,
        strong_buy_worked_percentage=sb_wp,
        strong_buy_didnt_work=sb_d,
        strong_buy_didnt_work_percentage=sb_dp,
        buy_worked=b_w,
        buy_worked_percentage=b_wp,
        buy_didnt_work=b_d,
        buy_didnt_work_percentage=b_dp,
        hold=hold_count,
        strong_sell_worked=ss_w,
        strong_sell_worked_percentage=ss_wp,
        strong_sell_didnt_work=ss_d,
        strong_sell_didnt_work_percentage=ss_dp,
        sell_worked=s_w,
        sell_worked_percentage=s_wp,
        sell_didnt_work=s_d,
        sell_didnt_work_percentage=s_dp,
    )

    return stats


__all__ = [
    "compute_backtest_stats_for_country_symbol",
    "BHS_STRONG_BUY",
    "BHS_BUY",
    "BHS_HOLD",
    "BHS_SELL",
    "BHS_STRONG_SELL",
    "WNDW_WORKED",
    "WNDW_DIDNT_WORK",
]
