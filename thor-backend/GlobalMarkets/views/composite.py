from datetime import datetime, time, timedelta
import pytz
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Market
from ..models.constants import CONTROL_MARKET_WEIGHTS

# Default control markets config (no DB required)
CONTROL_MARKETS_DEFAULTS = {
    'Japan':        {'timezone': 'Asia/Tokyo',        'open': time(9, 0),  'close': time(15, 0)},
    'China':        {'timezone': 'Asia/Shanghai',     'open': time(9, 30), 'close': time(15, 0)},
    'India':        {'timezone': 'Asia/Kolkata',      'open': time(9, 15), 'close': time(15, 30)},
    'Germany':      {'timezone': 'Europe/Berlin',     'open': time(9, 0),  'close': time(17, 30)},
    'United Kingdom': {'timezone': 'Europe/London',   'open': time(8, 0),  'close': time(16, 30)},
    'Pre_USA':      {'timezone': 'America/New_York',  'open': time(8, 30), 'close': time(9, 30)},
    'USA':          {'timezone': 'America/New_York',  'open': time(9, 30), 'close': time(16, 0)},
    'Canada':       {'timezone': 'America/Toronto',   'open': time(9, 30), 'close': time(16, 0)},
    'Mexico':       {'timezone': 'America/Mexico_City','open': time(8, 30), 'close': time(15, 0)},
}


def _is_open_now(tz_name: str, open_t: time, close_t: time) -> bool:
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False

    def _localize_safe(dt: datetime):
        try:
            return tz.localize(dt, is_dst=None)
        except (pytz.NonExistentTimeError, pytz.AmbiguousTimeError):
            try:
                return tz.localize(dt, is_dst=True)
            except Exception:
                return tz.localize(dt, is_dst=False)

    open_dt = _localize_safe(datetime(now.year, now.month, now.day, open_t.hour, open_t.minute))
    close_dt = _localize_safe(datetime(now.year, now.month, now.day, close_t.hour, close_t.minute))
    if open_t > close_t:
        # Overnight
        close_dt += timedelta(days=1)
    return open_dt <= now <= close_dt if open_t <= close_t else (now >= open_dt or now <= close_dt)


@api_view(['GET'])
@permission_classes([AllowAny])
def control_markets(request):
    """
    Return control markets. If DB rows exist, include DB fields (weight/is_control_market).
    Otherwise, compute from static defaults (no DB required).
    """
    results = []
    for country, weight in CONTROL_MARKET_WEIGHTS.items():
        db_obj = Market.objects.filter(country=country).first()
        defaults = CONTROL_MARKETS_DEFAULTS[country]
        tz = defaults['timezone']
        open_t = defaults['open']
        close_t = defaults['close']

        if db_obj:
            status = db_obj.get_market_status()
            state = status.get("current_state") if isinstance(status, dict) else None
            is_open_now = state in {"OPEN", "PRECLOSE"}

            results.append({
                'country': country,
                'display_name': db_obj.get_display_name(),
                'timezone_name': db_obj.timezone_name,
                'market_open_time': db_obj.market_open_time.strftime('%H:%M'),
                'market_close_time': db_obj.market_close_time.strftime('%H:%M'),
                'is_open_now': is_open_now,
                'state': state,
                'is_control_market': db_obj.is_control_market,
                'weight': float(db_obj.weight),
                'has_db_record': True,
            })
        else:
            active = _is_open_now(tz, open_t, close_t)

            results.append({
                'country': country,
                'display_name': country,
                'timezone_name': tz,
                'market_open_time': f"{open_t.hour:02d}:{open_t.minute:02d}",
                'market_close_time': f"{close_t.hour:02d}:{close_t.minute:02d}",
                'is_open_now': active,
                'state': None,
                'is_control_market': True,
                'weight': float(weight),
                'has_db_record': False,
            })
    return Response({'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def composite_index(request):
    """
    Return the weighted composite index using DB model if available, otherwise fallback calculation.
    """
    # Prefer DB-backed method if any control markets exist
    if Market.objects.filter(is_control_market=True).exists():
        data = Market.calculate_global_composite()
        return Response(data)

    # Fallback: compute from defaults without DB
    composite_score = 0.0
    active_count = 0
    contributions = {}

    for country, weight in CONTROL_MARKET_WEIGHTS.items():
        defaults = CONTROL_MARKETS_DEFAULTS[country]
        active = _is_open_now(defaults['timezone'], defaults['open'], defaults['close'])
        contribution = (weight * 100.0) if active else 0.0
        composite_score += contribution
        active_count += 1 if active else 0
        contributions[country] = {
            'weight': weight * 100.0,
            'active': active,
            'contribution': contribution,
        }

    # Rough session phase by UTC hour
    now_utc = datetime.now(pytz.UTC)
    h = now_utc.hour
    if 0 <= h < 8:
        phase = 'ASIAN'
    elif 8 <= h < 14:
        phase = 'EUROPEAN'
    elif 14 <= h < 21:
        phase = 'AMERICAN'
    else:
        phase = 'OVERLAP'

    return Response({
        'composite_score': round(composite_score, 2),
        'active_markets': active_count,
        'total_control_markets': len(CONTROL_MARKET_WEIGHTS),
        'max_possible': 100.0,
        'session_phase': phase,
        'contributions': contributions,
        'timestamp': now_utc.isoformat(),
    })
