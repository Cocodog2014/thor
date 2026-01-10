# ActAndPos/views/orders.py

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Order, Position
from ..serializers import (
    AccountSummarySerializer,
    OrderSerializer,
    PositionSerializer,
)
from .accounts import get_active_account
from .positions import _maybe_refresh_schwab_positions_and_balances


@api_view(["GET"])
def activity_today_view(request):
    """GET /actandpos/activity/today?account_id=123 – intraday order + position snapshot."""

    account = get_active_account(request)

    _maybe_refresh_schwab_positions_and_balances(request=request, account=account)

    today = timezone.localdate()
    base_qs = Order.objects.filter(account=account, time_placed__date=today)

    working = base_qs.filter(status="WORKING").order_by("-time_placed")
    filled = base_qs.filter(status="FILLED").order_by("-time_filled")
    canceled = base_qs.filter(status="CANCELED").order_by("-time_canceled")

    positions = Position.objects.filter(account=account).order_by("symbol")

    return Response(
        {
            "account": AccountSummarySerializer(account).data,
            "working_orders": OrderSerializer(working, many=True).data,
            "filled_orders": OrderSerializer(filled, many=True).data,
            "canceled_orders": OrderSerializer(canceled, many=True).data,
            "positions": PositionSerializer(positions, many=True).data,
            "account_status": {
                "ok_to_trade": account.ok_to_trade,
                "net_liq": account.net_liq,
                "day_trading_buying_power": account.day_trading_buying_power,
            },
        }
    )
