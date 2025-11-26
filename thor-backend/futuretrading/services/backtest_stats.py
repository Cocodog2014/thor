# FutureTrading/services/backtest_stats.py

"""
Backtest statistics for MarketSession trades.

For a given future symbol (YM, ES, NQ, ..., TOTAL) this module
computes how often each signal WORKED or DIDN'T WORK based on
historical MarketSession rows and returns values that can be copied
into the strong_buy_* / buy_* / hold_* / sell_* fields on a new row.

Usage:
    stats = compute_backtest_stats_for_future('YM')
    # returns a dict ready to merge into MarketSession(**data)
"""

from decimal import Decimal
from typing import Dict

from django.db.models import Count, Q

from FutureTrading.models.MarketSession import MarketSession


# Optional: change this to limit to the last N sessions per future
BACKTEST_MAX_SESSIONS = None  # e.g. 200, or None for "all history"


def _base_queryset(future: str):
    """
    Base queryset of historical rows for a given future, excluding
    PENDING / NEUTRAL outcomes.

    We only care about rows where a trade has actually resolved.
    """
    qs = MarketSession.objects.filter(
        future=future,
        wndw__in=['WORKED', 'DIDNT_WORK'],
    )

    if BACKTEST_MAX_SESSIONS:
        # Limit to the last N sessions for this future (optional)
        latest_sessions = (
            MarketSession.objects
            .filter(future=future)
            .order_by('-session_number')
            .values_list('session_number', flat=True)
            .distinct()[:BACKTEST_MAX_SESSIONS]
        )
        qs = qs.filter(session_number__in=list(latest_sessions))

    return qs


def _signal_stats(qs, signal: str):
    """
    Return (worked_count, didnt_work_count, worked_pct, didnt_work_pct)
    for a given signal within the queryset.
    """
    worked = qs.filter(bhs=signal, wndw='WORKED').count()
    didnt = qs.filter(bhs=signal, wndw='DIDNT_WORK').count()
    total = worked + didnt

    if total > 0:
        worked_pct = (Decimal(worked) / Decimal(total)) * Decimal('100')
        didnt_pct = (Decimal(didnt) / Decimal(total)) * Decimal('100')
    else:
        worked_pct = None
        didnt_pct = None

    return worked, didnt, worked_pct, didnt_pct


def compute_backtest_stats_for_future(future: str) -> Dict[str, Decimal | None]:
    """
    Compute backtest statistics for a single future symbol.

    Returns a dict whose keys line up with the MarketSession fields:
      - strong_buy_worked
      - strong_buy_worked_percentage
      - strong_buy_didnt_work
      - strong_buy_didnt_work_percentage
      - buy_worked
      - buy_worked_percentage
      - buy_didnt_work
      - buy_didnt_work_percentage
      - hold
      - strong_sell_worked
      - strong_sell_worked_percentage
      - strong_sell_didnt_work
      - strong_sell_didnt_work_percentage
      - sell_worked
      - sell_worked_percentage
      - sell_didnt_work
      - sell_didnt_work_percentage
    """

    qs = _base_queryset(future)

    # Strong Buy
    sb_w, sb_d, sb_wp, sb_dp = _signal_stats(qs, 'STRONG_BUY')
    # Buy
    b_w, b_d, b_wp, b_dp = _signal_stats(qs, 'BUY')
    # Hold: only track count (percentage field removed from model)
    hold_count = qs.filter(bhs='HOLD').count()
    # Strong Sell
    ss_w, ss_d, ss_wp, ss_dp = _signal_stats(qs, 'STRONG_SELL')
    # Sell
    s_w, s_d, s_wp, s_dp = _signal_stats(qs, 'SELL')

    return {
        'strong_buy_worked': sb_w or None,
        'strong_buy_worked_percentage': sb_wp,
        'strong_buy_didnt_work': sb_d or None,
        'strong_buy_didnt_work_percentage': sb_dp,

        'buy_worked': b_w or None,
        'buy_worked_percentage': b_wp,
        'buy_didnt_work': b_d or None,
        'buy_didnt_work_percentage': b_dp,

        'hold': hold_count or None,

        'strong_sell_worked': ss_w or None,
        'strong_sell_worked_percentage': ss_wp,
        'strong_sell_didnt_work': ss_d or None,
        'strong_sell_didnt_work_percentage': ss_dp,

        'sell_worked': s_w or None,
        'sell_worked_percentage': s_wp,
        'sell_didnt_work': s_d or None,
        'sell_didnt_work_percentage': s_dp,
    }
