from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Market
from ..models.constants import CONTROL_MARKET_WEIGHTS


@api_view(['GET'])
@permission_classes([AllowAny])
def control_markets(request):
    """
    Return control markets sourced from DB-administered records. If a country from
    CONTROL_MARKET_WEIGHTS is missing in DB, surface it with has_db_record=False.
    """
    results = []
    for country, weight in CONTROL_MARKET_WEIGHTS.items():
        db_obj = Market.objects.filter(country=country).first()
        if db_obj:
            status = db_obj.get_market_status()
            state = status.get("current_state") if isinstance(status, dict) else None
            is_open_now = state in {"OPEN", "PRECLOSE"} or db_obj.is_market_open_now()

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
            results.append({
                'country': country,
                'display_name': country,
                'timezone_name': None,
                'market_open_time': None,
                'market_close_time': None,
                'is_open_now': False,
                'state': None,
                'is_control_market': False,
                'weight': float(weight),
                'has_db_record': False,
            })
    return Response({'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def composite_index(request):
    """
    Return the weighted composite index using DB-backed control markets.
    """
    if Market.objects.filter(is_control_market=True).exists():
        data = Market.calculate_global_composite()
        return Response(data)

    return Response({
        'composite_score': 0.0,
        'active_markets': 0,
        'total_control_markets': 0,
        'max_possible': 100.0,
        'session_phase': None,
        'contributions': {},
        'timestamp': None,
        'detail': 'No control markets found in DB; configure via admin.',
    })
