from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Position
from ..serializers import AccountSummarySerializer, PositionSerializer
from .accounts import get_active_account


@api_view(["GET"])
def positions_view(request):
    """GET /api/positions?account_id=123 – current positions plus account summary."""

    account = get_active_account(request)

    positions = Position.objects.filter(account=account).order_by("symbol")

    return Response(
        {
            "account": AccountSummarySerializer(account).data,
            "positions": PositionSerializer(positions, many=True).data,
        }
    )
