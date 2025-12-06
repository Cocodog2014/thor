# ActAndPos/views/paper_orders.py

from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Account, Order, Position
from ..serializers import (
    AccountSummarySerializer,
    OrderSerializer,
    PositionSerializer,
    TradeSerializer,
)
from ..services.paper_engine import (
    PaperOrderParams,
    place_paper_order,
    InsufficientBuyingPower,
    InvalidPaperOrder,
    PaperTradingError,
)


def _to_decimal(val):
    if val is None or val == "":
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


@api_view(["POST"])
def paper_order_create_view(request):
    """
    POST /api/actandpos/paper/orders

    Create a PAPER order, immediately fill it, and return the updated snapshot.
    """

    data = request.data

    # account
    try:
        account_id = int(data.get("account_id"))
    except (TypeError, ValueError):
        return Response(
            {"detail": "account_id is required and must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        account = Account.objects.get(pk=account_id)
    except Account.DoesNotExist:
        return Response({"detail": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

    # core fields
    symbol = data.get("symbol")
    side = data.get("side")
    order_type = data.get("order_type") or "MKT"
    asset_type = data.get("asset_type") or "EQ"
    quantity_raw = data.get("quantity")

    if not symbol or not side or quantity_raw in (None, ""):
        return Response(
            {"detail": "symbol, side and quantity are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        quantity = Decimal(str(quantity_raw))
    except Exception:
        return Response(
            {"detail": "quantity must be a number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit_price = _to_decimal(data.get("limit_price"))
    stop_price = _to_decimal(data.get("stop_price"))

    params = PaperOrderParams(
        account=account,
        symbol=symbol,
        asset_type=asset_type,
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
        commission=Decimal("0"),
        fees=Decimal("0"),
    )

    try:
        order, trade, _position, account = place_paper_order(params)
    except InsufficientBuyingPower as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except InvalidPaperOrder as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except PaperTradingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    positions = Position.objects.filter(account=account).order_by("symbol")

    return Response(
        {
            "order": OrderSerializer(order).data,
            "trade": TradeSerializer(trade).data,
            "account": AccountSummarySerializer(account).data,
            "positions": PositionSerializer(positions, many=True).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def paper_order_cancel_view(request, pk: int):
    """
    POST /api/actandpos/paper/orders/<pk>/cancel

    Cancel a WORKING paper order. No position/cash changes.
    """

    try:
        order = Order.objects.select_related("account").get(pk=pk)
    except Order.DoesNotExist:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    account = order.account
    if account.broker != "PAPER":
        return Response(
            {"detail": "Only PAPER orders can be canceled here."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if order.status != "WORKING":
        return Response(
            {
                "detail": f"Only WORKING orders can be canceled "
                f"(current status: {order.status})."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    from django.utils import timezone

    now = timezone.now()
    order.status = "CANCELED"
    order.time_canceled = now
    order.time_last_update = now
    order.save(update_fields=["status", "time_canceled", "time_last_update"])

    return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
