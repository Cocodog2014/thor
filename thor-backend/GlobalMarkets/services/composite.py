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

    for market in cls.objects.filter(is_control_market=True, is_active=True):
        weight = float(market.weight)
        market_name = market.get_display_name()

        if market.is_market_open_now():
            contribution = weight * 100
            composite_score += contribution
            active_count += 1
            contributions[market_name] = {
                'weight': weight * 100,
                'active': True,
                'contribution': contribution
            }
        else:
            contributions[market_name] = {
                'weight': weight * 100,
                'active': False,
                'contribution': 0
            }

    return {
        'composite_score': round(composite_score, 2),
        'active_markets': active_count,
        'total_control_markets': 9,
        'max_possible': 100.0,
        'session_phase': _determine_session_phase(),
        'contributions': contributions,
        'timestamp': datetime.now(pytz.UTC).isoformat()
    }
