from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Market


@api_view(['GET'])
@permission_classes([AllowAny])
def markets_overview(request):
    """Return all markets from the DB (no hardcoded schedules)."""
    markets = Market.objects.all().order_by('country')
    results = []

    for market in markets:
        status = market.get_market_status()
        state = status.get("current_state") if isinstance(status, dict) else None
        is_open_now = state in {"OPEN", "PRECLOSE"} or market.is_market_open_now()

        results.append({
            'country': market.country,
            'display_name': market.get_display_name(),
            'timezone_name': market.timezone_name,
            'market_open_time': market.market_open_time.strftime('%H:%M'),
            'market_close_time': market.market_close_time.strftime('%H:%M'),
            'is_open_now': is_open_now,
            'state': state,
            'has_db_record': True,
        })

    return Response({'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def composite_index(request):
    """
    Return composite using all active markets. If none are active, return a stub.
    """
    if Market.objects.filter(is_active=True).exists():
        data = Market.calculate_global_composite()
        return Response(data)

    return Response({
        'detail': 'No active markets configured; add markets in admin to enable composite.',
        'composite_score': 0.0,
        'active_markets': 0,
        'total_control_markets': 0,
        'max_possible': 100.0,
        'approx_region_phase_utc': None,
        'contributions': {},
        'timestamp': None,
    })
