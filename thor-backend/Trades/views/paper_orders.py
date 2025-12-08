from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.models import Account, Order, Position
from ActAndPos.serializers import (
    AccountSummarySerializer,
    OrderSerializer,
    PositionSerializer,
)
from ActAndPos.services.order_engine import (
    OrderParams,
    place_order,
    InsufficientBuyingPower,
    InvalidPaperOrder,
    PaperTradingError,
)
from ActAndPos.views.accounts import get_active_account

from ..serializers import TradeSerializer


def _parse_decimal(value, field_name: str, allow_null: bool = False):
    if value in (None, "", "null"):
        if allow_null:
            return None
        raise ValueError(f"{field_name} is required.")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid {field_name}.")


def _to_decimal(val):
    if val is None or val == "":
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


@api_view(["POST"])
def order_create_active_view(request):
    """
    POST /trades/orders/active

    Create an order for the *active* account (from session or ?account_id=),
    route it through the unified order_engine, and return the updated snapshot.
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

    params = OrderParams(
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
        order, trade, position, account = place_order(params)
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


@api_view(["POST"])
def order_create_view(request):
    """
    POST /trades/orders

    Create an order for a specific account_id, immediately fill it via
    the order_engine, and return the updated snapshot.
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

    params = OrderParams(
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
        order, trade, _position, account = place_order(params)
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
def order_cancel_view(request, pk: int):
    """
    POST /trades/orders/<pk>/cancel

    Cancel a WORKING order. Right now it only allows PAPER accounts,
    but the name is generic so we can extend it to other brokers later.
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

    now = timezone.now()
    order.status = "CANCELED"
    order.time_canceled = now
    order.time_last_update = now
    order.save(update_fields=["status", "time_canceled", "time_last_update"])

    return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

