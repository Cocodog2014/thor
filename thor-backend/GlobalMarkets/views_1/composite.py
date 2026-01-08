from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Market


@api_view(['GET'])
@permission_classes([AllowAny])
def composite_index(request):
    """
    Return composite using all active markets (control flag removed). If none are active, return a stub.
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
