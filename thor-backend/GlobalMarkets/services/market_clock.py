from datetime import datetime, time, timedelta
import pytz

from GlobalMarkets.models.constants import _DEFAULT_MARKET_TZ


def _resolve_timezone(market):
    tz_name = (market.timezone_name or "").strip()
    if not tz_name:
        return None
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return None


def get_market_time(market):
    tz = _resolve_timezone(market) or _DEFAULT_MARKET_TZ
    try:
        now = datetime.now(tz)
        return {
            'datetime': now,
            'year': now.year,
            'month': now.month,
            'date': now.day,
            'day': now.strftime('%a'),
            'day_number': now.weekday(),
            'time': now.strftime('%H:%M:%S'),
            'formatted_12h': now.strftime('%I:%M:%S %p'),
            'formatted_24h': now.strftime('%H:%M:%S'),
            'timestamp': now.timestamp(),
            'utc_offset': now.strftime('%z'),
            'dst_active': bool(now.dst()),
        }
    except Exception:
        return None


def is_market_open_now(market):
    market_time_data = get_market_time(market)
    if not market_time_data:
        return False
    if market_time_data.get('day_number', 0) >= 5:
        return False

    current_time = market_time_data['datetime'].time()

    if market.market_open_time <= market.market_close_time:
        return market.market_open_time <= current_time <= market.market_close_time
    else:
        return current_time >= market.market_open_time or current_time <= market.market_close_time


def get_market_status(market):
    market_time = get_market_time(market)
    if not market_time or not market.is_active:
        return None

    tz = _resolve_timezone(market) or _DEFAULT_MARKET_TZ
    now_local = market_time['datetime']

    def is_holiday(d: datetime) -> bool:
        local_date = d.date()
        try:
            return market.holidays.filter(date=local_date, full_day=True).exists()
        except Exception:
            return False

    def is_trading_day(d: datetime) -> bool:
        return d.weekday() < 5 and not is_holiday(d)

    def combine_local(d: datetime, t: time) -> datetime:
        naive = datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)
        return tz.localize(naive)

    open_today = combine_local(now_local, market.market_open_time)
    close_today = combine_local(now_local, market.market_close_time)

    if market.market_open_time > market.market_close_time:
        close_today = close_today + timedelta(days=1)

    def next_trading_day(start: datetime) -> datetime:
        d = start + timedelta(days=1)
        while not is_trading_day(d):
            d += timedelta(days=1)
        return d

    def compute_next_open(now_dt: datetime) -> datetime:
        if is_trading_day(now_dt):
            if now_dt < open_today:
                return open_today
            elif now_dt <= close_today:
                nd = next_trading_day(now_dt)
                return combine_local(nd, market.market_open_time)
        nd = next_trading_day(now_dt)
        return combine_local(nd, market.market_open_time)

    def compute_next_close(now_dt: datetime) -> datetime:
        if is_trading_day(now_dt) and open_today <= now_dt <= close_today:
            return close_today
        if is_trading_day(now_dt) and now_dt < open_today:
            return close_today
        nd = next_trading_day(now_dt)
        close_nd = combine_local(nd, market.market_close_time)
        if market.market_open_time > market.market_close_time:
            close_nd = close_nd + timedelta(days=1)
        return close_nd

    weekend = market_time.get('day_number', 0) >= 5
    holiday_today = is_holiday(now_local)
    in_hours = False if (weekend or holiday_today) else is_market_open_now(market)

    PREOPEN_MIN = 60
    PRECLOSE_MIN = 15

    next_open_at_dt = compute_next_open(now_local)
    next_close_at_dt = compute_next_close(now_local)

    if holiday_today:
        current_state = 'HOLIDAY_CLOSED'
        next_event = 'open'
        target_dt = next_open_at_dt
    elif in_hours:
        if (next_close_at_dt - now_local) <= timedelta(minutes=PRECLOSE_MIN):
            current_state = 'PRECLOSE'
        else:
            current_state = 'OPEN'
        next_event = 'close'
        target_dt = next_close_at_dt
    else:
        if is_trading_day(now_local) and now_local < open_today and (open_today - now_local) <= timedelta(minutes=PREOPEN_MIN):
            current_state = 'PREOPEN'
        else:
            current_state = 'CLOSED'
        next_event = 'open'
        target_dt = next_open_at_dt

    seconds_to_next_event = max(0, int((target_dt - now_local).total_seconds()))
    effective_status = 'CLOSED' if weekend else market.status

    return {
        'country': market.country,
        'timezone': market.timezone_name,
        'current_time': market_time,
        'market_open': market.market_open_time.strftime('%H:%M'),
        'market_close': market.market_close_time.strftime('%H:%M'),
        'is_in_trading_hours': in_hours,
        'status': effective_status,
        'should_collect_data': False if weekend else should_collect_data(market),
        'current_state': current_state,
        'next_open_at': next_open_at_dt.isoformat(),
        'next_close_at': next_close_at_dt.isoformat(),
        'next_event': next_event,
        'seconds_to_next_event': seconds_to_next_event,
        'is_holiday_today': holiday_today,
    }


def should_collect_data(market):
    market_time_data = get_market_time(market)
    if not market_time_data:
        return False
    if market_time_data.get('day_number', 0) >= 5:
        return False
    return market.is_active and market.status == 'OPEN'
