# GlobalMarkets/services.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional

from zoneinfo import ZoneInfo
from django.utils import timezone

from GlobalMarkets.models import Market, MarketSession, MarketHoliday


@dataclass(frozen=True)
class ComputedMarketStatus:
    key: str
    name: str
    timezone_name: str

    as_of_utc: datetime
    local_dt: datetime
    local_date: datetime.date
    weekday: int  # 0=Mon..6=Sun

    status: str  # CLOSED / PREMARKET / OPEN
    reason: str  # "HOLIDAY" | "WEEKLY_CLOSED" | "OUTSIDE_HOURS" | "IN_SESSION" | ...
    next_transition_utc: Optional[datetime]


def _tz(market: Market) -> ZoneInfo:
    try:
        return ZoneInfo(market.timezone_name)
    except Exception:
        # Fail-safe: treat as UTC if misconfigured
        return ZoneInfo("UTC")


def _combine_local(tz: ZoneInfo, d, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=tz)


def _get_session_for_today(market: Market, weekday: int) -> Optional[MarketSession]:
    return market.sessions.filter(weekday=weekday).first()


def _get_holiday_for_today(market: Market, local_date) -> Optional[MarketHoliday]:
    return market.holidays.filter(date=local_date).first()


def compute_market_status(market: Market, *, now_utc: Optional[datetime] = None) -> Optional[ComputedMarketStatus]:
    if not getattr(market, "is_active", True):
        return None

    now_utc = now_utc or timezone.now()
    tz = _tz(market)
    local_dt = now_utc.astimezone(tz)
    local_date = local_dt.date()
    weekday = local_dt.weekday()

    # Holiday override
    holiday = _get_holiday_for_today(market, local_date)
    if holiday and holiday.is_closed:
        nxt = next_transition_utc(market, now_utc=now_utc)
        return ComputedMarketStatus(
            key=market.key,
            name=market.name,
            timezone_name=market.timezone_name,
            as_of_utc=now_utc,
            local_dt=local_dt,
            local_date=local_date,
            weekday=weekday,
            status=Market.Status.CLOSED,
            reason="HOLIDAY",
            next_transition_utc=nxt,
        )

    session = _get_session_for_today(market, weekday)
    if not session or session.is_closed:
        nxt = next_transition_utc(market, now_utc=now_utc)
        return ComputedMarketStatus(
            key=market.key,
            name=market.name,
            timezone_name=market.timezone_name,
            as_of_utc=now_utc,
            local_dt=local_dt,
            local_date=local_date,
            weekday=weekday,
            status=Market.Status.CLOSED,
            reason="WEEKLY_CLOSED",
            next_transition_utc=nxt,
        )

    # Determine today's close time (early close override)
    close_time = holiday.early_close_time if (holiday and holiday.early_close_time) else session.close_time
    open_time = session.open_time
    pre_time = session.premarket_open_time

    # If open/close not configured, treat as closed
    if not open_time or not close_time:
        nxt = next_transition_utc(market, now_utc=now_utc)
        return ComputedMarketStatus(
            key=market.key,
            name=market.name,
            timezone_name=market.timezone_name,
            as_of_utc=now_utc,
            local_dt=local_dt,
            local_date=local_date,
            weekday=weekday,
            status=Market.Status.CLOSED,
            reason="MISSING_HOURS",
            next_transition_utc=nxt,
        )

    open_dt = _combine_local(tz, local_dt, open_time)
    close_dt = _combine_local(tz, local_dt, close_time)
    if close_time < open_time:
        # Overnight session
        close_dt += timedelta(days=1)
        if local_dt.time() < open_time:
            # If we're after midnight before open, the "open" belongs to today; close is next day; OK.
            pass

    pre_dt = _combine_local(tz, local_dt, pre_time) if pre_time else None
    if pre_dt and open_time and pre_time and open_time < pre_time and close_time >= open_time:
        # weird config; ignore premarket if it is after open
        pre_dt = None

    # Compute status
    status = Market.Status.CLOSED
    reason = "OUTSIDE_HOURS"
    if pre_dt and pre_dt <= local_dt < open_dt:
        status = Market.Status.PREMARKET
        reason = "IN_PREMARKET"
    elif open_dt <= local_dt < close_dt:
        status = Market.Status.OPEN
        reason = "IN_SESSION"

    nxt = _next_transition_from_times(local_dt, pre_dt, open_dt, close_dt)
    nxt_utc = nxt.astimezone(timezone.utc) if nxt else None

    return ComputedMarketStatus(
        key=market.key,
        name=market.name,
        timezone_name=market.timezone_name,
        as_of_utc=now_utc,
        local_dt=local_dt,
        local_date=local_date,
        weekday=weekday,
        status=status,
        reason=reason,
        next_transition_utc=nxt_utc,
    )


def _next_transition_from_times(local_now: datetime, pre_dt: Optional[datetime], open_dt: datetime, close_dt: datetime) -> Optional[datetime]:
    candidates: list[datetime] = []
    if pre_dt and local_now < pre_dt:
        candidates.append(pre_dt)
    if local_now < open_dt:
        candidates.append(open_dt)
    if local_now < close_dt:
        candidates.append(close_dt)
    return min(candidates) if candidates else None


def next_transition_utc(market: Market, *, now_utc: Optional[datetime] = None) -> Optional[datetime]:
    """
    Find the next transition (premarket/open/close) in UTC by scanning forward a limited window.
    Keeps it simple: look up to 14 days ahead.
    """
    now_utc = now_utc or timezone.now()
    tz = _tz(market)
    local_now = now_utc.astimezone(tz)

    for offset in range(0, 14):
        day = (local_now + timedelta(days=offset))
        local_date = day.date()
        weekday = day.weekday()

        holiday = _get_holiday_for_today(market, local_date)
        if holiday and holiday.is_closed:
            continue

        session = _get_session_for_today(market, weekday)
        if not session or session.is_closed:
            continue

        open_time = session.open_time
        close_time = (holiday.early_close_time if (holiday and holiday.early_close_time) else session.close_time)
        pre_time = session.premarket_open_time

        if not open_time or not close_time:
            continue

        open_dt = _combine_local(tz, day, open_time)
        close_dt = _combine_local(tz, day, close_time)
        if close_time < open_time:
            close_dt += timedelta(days=1)

        pre_dt = _combine_local(tz, day, pre_time) if pre_time else None

        # choose the first candidate after local_now
        candidates = [dt for dt in [pre_dt, open_dt, close_dt] if dt and dt > local_now]
        if candidates:
            return min(candidates).astimezone(timezone.utc)

    return None
