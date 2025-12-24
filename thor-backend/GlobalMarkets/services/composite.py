from datetime import datetime
import pytz


def _determine_session_phase():
    now_utc = datetime.now(pytz.UTC)
    hour = now_utc.hour
    if 0 <= hour < 8:
        return 'ASIAN'
    elif 8 <= hour < 14:
        return 'EUROPEAN'
    elif 14 <= hour < 21:
        return 'AMERICAN'
    else:
        return 'OVERLAP'


def calculate_global_composite(cls):
    composite_score = 0.0
    active_count = 0
    contributions = {}

    markets = list(cls.objects.filter(is_active=True))
    total_control_markets = len(markets)
    weight_each = 1.0 / total_control_markets if total_control_markets else 0.0

    for market in markets:
        weight = weight_each
        market_name = market.get_display_name()

        status = None
        try:
            status = market.get_market_status()
        except Exception:
            status = None

        current_state = status.get('current_state') if isinstance(status, dict) else None
        is_active_state = current_state in {'OPEN', 'PRECLOSE'}

        if status is None:
            # Fallback to legacy open check if status unavailable
            is_active_state = market.is_market_open_now()

        if is_active_state:
            contribution = weight * 100
            composite_score += contribution
            active_count += 1
            contributions[market_name] = {
                'weight': weight * 100,
                'active': True,
                'contribution': contribution,
                'state': current_state,
            }
        else:
            contributions[market_name] = {
                'weight': weight * 100,
                'active': False,
                'contribution': 0,
                'state': current_state,
            }

    return {
        'composite_score': round(composite_score, 2),
        'active_markets': active_count,
        'total_control_markets': total_control_markets,
        'max_possible': 100.0,
        'session_phase': _determine_session_phase(),
        'contributions': contributions,
        'timestamp': datetime.now(pytz.UTC).isoformat()
    }
