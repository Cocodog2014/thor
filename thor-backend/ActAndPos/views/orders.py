# ActAndPos/views/orders.py

from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Order, Position
from ..serializers import (
    AccountSummarySerializer,
    OrderSerializer,
    PositionSerializer,
)
from ..services.paper_engine import (
    PaperOrderParams,
    place_paper_order,
    InvalidPaperOrder,
    InsufficientBuyingPower,
)
from .accounts import get_active_account


@api_view(["GET"])
def activity_today_view(request):
    """GET /actandpos/activity/today?account_id=123 – intraday order + position snapshot."""

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

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


def _parse_decimal(value, field_name: str, allow_null: bool = False):
    if value in (None, "", "null"):
        if allow_null:
            return None
        raise ValueError(f"{field_name} is required.")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid {field_name}.")


@api_view(["POST"])
def paper_order_view(request):
    """
    POST /actandpos/paper/order

    Body:
    {
      "symbol": "ES",
      "asset_type": "FUT",
      "side": "BUY",
      "quantity": 1,
      "order_type": "MKT" | "LMT" | "STP" | "STP_LMT",
      "limit_price": 4800.25,   // for LMT / STP_LMT
      "stop_price": null        // optional
    }

    Uses the active account (or ?account_id=).
    """

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data

    symbol = (data.get("symbol") or "").upper().strip()
    asset_type = (data.get("asset_type") or "EQ").upper()
    side = (data.get("side") or "").upper()
    order_type = (data.get("order_type") or "MKT").upper()

    try:
        quantity = _parse_decimal(data.get("quantity"), "quantity")
        limit_price = _parse_decimal(
            data.get("limit_price"), "limit_price", allow_null=True
        )
        stop_price = _parse_decimal(
            data.get("stop_price"), "stop_price", allow_null=True
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    params = PaperOrderParams(
        account=account,
        symbol=symbol,
        asset_type=asset_type,
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
    )

    try:
        order, trade, position, account = place_paper_order(params)
    except InvalidPaperOrder as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except InsufficientBuyingPower as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "account": AccountSummarySerializer(account).data,
            "order": OrderSerializer(order).data,
            "position": PositionSerializer(position).data
            if position is not None
            else None,
        },
        status=status.HTTP_201_CREATED,
    )
