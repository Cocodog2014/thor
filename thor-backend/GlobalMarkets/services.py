"""GlobalMarkets services.

This module is intentionally small and import-stable.

It provides:
- Market clock computation (`compute_market_status`)
- Lightweight country normalization helpers
- Helpers for other apps (ThorTrading, etc.) to list "control" markets

NOTE
----
Historically, some callers imported `GlobalMarkets.services.active_markets`.
GlobalMarkets is now a single-module services layer; keep the helpers here.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import Iterable, Optional

from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.models.market_holiday import MarketHoliday
from GlobalMarkets.normalize import normalize_country_code

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


def _as_utc(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _localize(market: Market, now_utc: datetime) -> datetime:
    """Convert UTC -> market local time."""
    if ZoneInfo is None:
        return now_utc
    tz = ZoneInfo(market.timezone_name)
    return now_utc.astimezone(tz)


def _dt_local(local_now: datetime, t: time) -> datetime:
    """Build a local datetime on local_now's date at time t."""
    return local_now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)


def _next_day(local_now: datetime) -> datetime:
    return (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _get_holiday(local_date) -> Optional[MarketHoliday]:
    """Get US holiday for given date (applies to all markets)."""
    return MarketHoliday.objects.filter(date=local_date).first()


def compute_market_status(market: Market, *, now_utc: Optional[datetime] = None) -> MarketComputation:
    """
    Compute current market status and the next transition time.

    Simplified Rules:
      1) Weekends (Sat/Sun) = CLOSED automatically
      2) US Holiday = CLOSED (or early close) - applies to all markets
      3) Use Market.open_time and Market.close_time for Monday-Friday trading
    """
    now_utc = now_utc or timezone.now()
    now_utc = _as_utc(now_utc)

    local_now = _localize(market, now_utc)
    local_date = local_now.date()
    weekday = int(local_now.weekday())

    # Check for US holiday (applies to all markets)
    holiday = _get_holiday(local_date)
    if holiday and holiday.is_closed:
        # Closed all day - next transition is next business day
        tomorrow = _next_day(local_now)
        tomorrow_weekday = int(tomorrow.weekday())
        while tomorrow_weekday >= 5:  # Skip weekends
            tomorrow += timedelta(days=1)
            tomorrow_weekday = int(tomorrow.weekday())
        next_utc = _as_utc(_dt_local(tomorrow, market.open_time)) if market.open_time else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="us_holiday")

    # Check if weekend (Saturday=5, Sunday=6)
    if weekday >= 5:
        # Find next Monday
        days_until_monday = 7 - weekday if weekday == 6 else 2
        tomorrow = local_now + timedelta(days=days_until_monday)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        next_utc = _as_utc(_dt_local(tomorrow, market.open_time)) if market.open_time else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="weekend")

    # Use market's default open/close times
    open_t = market.open_time
    close_t = market.close_time

    # Apply early close override if present
    if holiday and (not holiday.is_closed) and holiday.early_close_time:
        close_t = holiday.early_close_time

    # If we have no open/close times, treat as closed
    if not open_t or not close_t:
        tomorrow = _next_day(local_now)
        next_utc = _as_utc(_dt_local(tomorrow, market.open_time)) if market.open_time else None
        return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="missing_times")

    dt_open = _dt_local(local_now, open_t)
    dt_close = _dt_local(local_now, close_t)

    # Determine status + next transition
    if local_now < dt_open:
        # Before market open
        return MarketComputation(
            status=Market.Status.CLOSED,
            next_transition_utc=_as_utc(dt_open),
            reason="before_open",
        )

    if dt_open <= local_now < dt_close:
        # Market is open
        return MarketComputation(
            status=Market.Status.OPEN,
            next_transition_utc=_as_utc(dt_close),
            reason="open",
        )

    # After close -> closed until next business day
    tomorrow = _next_day(local_now)
    tomorrow_weekday = int(tomorrow.weekday())
    while tomorrow_weekday >= 5:  # Skip weekends
        tomorrow += timedelta(days=1)
        tomorrow_weekday = int(tomorrow.weekday())
    
    next_utc = _as_utc(_dt_local(tomorrow, market.open_time)) if market.open_time else None
    return MarketComputation(status=Market.Status.CLOSED, next_transition_utc=next_utc, reason="after_close")


# -----------------------------------------------------------------------------
# Control markets helpers
# -----------------------------------------------------------------------------
def get_control_markets(*, require_session_capture: bool = False) -> Iterable[Market]:
    """Return the set of markets other apps should treat as "controlled".

    Today this is simply "active markets".

    The `require_session_capture` flag is kept for compatibility with older
    callers; GlobalMarkets no longer owns any per-market study flags.
    """
    _ = require_session_capture
    return Market.objects.filter(is_active=True).order_by("sort_order", "name")


def get_control_countries(*, require_session_capture: bool = False) -> list[str]:
    """Return normalized country codes for controlled markets."""
    markets = get_control_markets(require_session_capture=require_session_capture)
    out: list[str] = []
    seen: set[str] = set()
    for m in markets:
        raw = getattr(m, "country", None) or getattr(m, "key", None)
        code = normalize_country_code(raw) or (str(raw).strip().upper() if raw else None)
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def is_known_country(country: str | None, *, controlled: set[str] | None = None) -> bool:
    """Return True if `country` is allowed/known for the current runtime."""
    code = normalize_country_code(country)
    if not code:
        return False
    if controlled is None:
        return True
    return code in {normalize_country_code(c) or c for c in controlled}

