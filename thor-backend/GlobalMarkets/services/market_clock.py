# Path: GlobalMarkets/services/market_clock.py
#
# GlobalMarkets market clock computation (single source of truth)
# --------------------------------------------------------------
# What this file does:
#   - Computes the current market status (CLOSED / PREMARKET / OPEN)
#   - Computes the next_transition_utc (when the status will change next)
#
# What this file does NOT do:
#   - No loops / timers / heartbeats
#   - No DB writes
#   - No websocket broadcasts
#
# Those responsibilities belong to:
#   - A runner/job (Thor realtime engine job, or a management command) to call compute_market_status()
#   - Market.mark_status() to persist transitions
#   - signals.py / websocket bridge to notify the frontend on transitions

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional

from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.models.market_session import MarketSession
from GlobalMarkets.models.market_holiday import MarketHoliday

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


@dataclass(frozen=True)
class MarketComputation:
    """Return object for market state computation."""
    status: str
    next_transition_utc: Optional[datetime]
    reason: str = ""


def _as_utc(dt: datetime) -> datetime:
    """Ensure an aware UTC datetime."""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=timezone.utc)
    return dt.astimezone(timezone.utc)


def _localize(market: Market, now_utc: datetime) -> datetime:
    """Convert UTC -> market local time."""
    if ZoneInfo is None:
        # Fallback: if zoneinfo isn't available, assume now_utc is already usable
        return now_utc
    tz = ZoneInfo(market.timezone_name)
    return now_utc.astimezone(tz)


def _dt_local(local_now: datetime, t: time) -> datetime:
    """Build a local datetime on local_now's date at time t."""
    return local_now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)


def _next_day(local_now: datetime) -> datetime:
    return (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _get_session(market: Market, weekday: int) -> Optional[MarketSession]:
    return (
        MarketSession.objects
        .filter(market=market, weekday=weekday)
        .first()
    )


def _get_holiday(market: Market, local_date) -> Optional[MarketHoliday]:
    return (
        MarketHoliday.objects
        .filter(market=market, date=local_date)
        .first()
    )


def compute_market_status(market: Market, *, now_utc: Optional[datetime] = None) -> MarketComputation:
    """
    Compute current market status and the next transition time.

    Rules:
      1) Holiday override:
         - is_closed=True => CLOSED all day (next transition = next day's earliest event)
         - early_close_time => CLOSES early today (use early close instead of session close)
      2) Weekly session:
         - if session.is_closed => CLOSED (next transition = next day's earliest event)
         - else use times:
             premarket_open_time (optional)
             open_time (optional)
             close_time (optional)
      3) Determine status by comparing local time to today's boundaries.
    """
    now_utc = now_utc or timezone.now()
    now_utc = _as_utc(now_utc)

    local_now = _localize(market, now_utc)
    local_date = local_now.date()
    weekday = int(local_now.weekday())

    holiday = _get_holiday(market, local_date)
    session = _get_session(market, weekday)

    # Helper: find earliest "start" time today (premarket or open) if present
    def earliest_start_time(s: Optional[MarketSession]) -> Optional[time]:
        if not s or s.is_closed:
            return None
        return s.premarket_open_time or s.open_time

    # If market is closed all day due to holiday
    if holiday and holiday.is_closed:
        # Next transition is "tomorrow's earliest start" (if any), else None (fallback used by runner/job)
        tomorrow = _next_day(local_now)
        tomorrow_session = _get_session(market, int(tomorrow.weekday()))
        start_t = earliest_start_time(tomorrow_session)
        next_utc = _as_utc(_dt_local(tomorrow, start_t)) if start_t else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="holiday_closed")

    # If no session configured or session closed
    if not session or session.is_closed:
        tomorrow = _next_day(local_now)
        tomorrow_session = _get_session(market, int(tomorrow.weekday()))
        start_t = earliest_start_time(tomorrow_session)
        next_utc = _as_utc(_dt_local(tomorrow, start_t)) if start_t else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="weekday_closed")

    # Build today's key boundaries
    pre_t = session.premarket_open_time
    open_t = session.open_time
    close_t = session.close_time

    # Apply early close override if present
    if holiday and (not holiday.is_closed) and holiday.early_close_time:
        close_t = holiday.early_close_time

    # If we have no open/close times, treat as closed (misconfigured)
    if not open_t or not close_t:
        tomorrow = _next_day(local_now)
        tomorrow_session = _get_session(market, int(tomorrow.weekday()))
        start_t = earliest_start_time(tomorrow_session)
        next_utc = _as_utc(_dt_local(tomorrow, start_t)) if start_t else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="missing_times")

    dt_open = _dt_local(local_now, open_t)
    dt_close = _dt_local(local_now, close_t)
    dt_pre = _dt_local(local_now, pre_t) if pre_t else None

    # Determine status + next transition
    if dt_pre and local_now < dt_pre:
        # Before premarket
        return MarketComputation(
            status=Market.Status.CLOSED,
            next_transition_utc=_as_utc(dt_pre),
            reason="before_premarket",
        )

    if dt_pre and dt_pre <= local_now < dt_open:
        # Premarket window
        return MarketComputation(
            status=Market.Status.PREMARKET,
            next_transition_utc=_as_utc(dt_open),
            reason="premarket",
        )

    if dt_open <= local_now < dt_close:
        # Regular open
        return MarketComputation(
            status=Market.Status.OPEN,
            next_transition_utc=_as_utc(dt_close),
            reason="open",
        )

    # After close -> closed until tomorrow’s earliest start
    tomorrow = _next_day(local_now)
    tomorrow_session = _get_session(market, int(tomorrow.weekday()))
    start_t = earliest_start_time(tomorrow_session)
    next_utc = _as_utc(_dt_local(tomorrow, start_t)) if start_t else None
    return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="after_close")
