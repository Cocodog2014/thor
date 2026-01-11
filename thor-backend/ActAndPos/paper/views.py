from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from ActAndPos.shared.marketdata import get_mark

from .models import PaperBalance, PaperFill, PaperOrder, PaperPosition
from .serializers import (
    PaperBalanceSerializer,
    PaperOrderSerializer,
    PaperPositionSerializer,
    PaperSubmitOrderSerializer,
)


DEFAULT_PAPER_CASH = Decimal("100000.00")


def _require_user(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")
    return user


def _default_account_key(user) -> str:
    return f"PAPER-{getattr(user, 'pk', '0')}"


def _resolve_account_key(request, *, user) -> str:
    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    return str(params.get("account_key") or params.get("account_id") or _default_account_key(user))


def _ensure_balance(user, account_key: str) -> PaperBalance:
    bal, _ = PaperBalance.objects.get_or_create(
        user=user,
        account_key=account_key,
        defaults={
            "currency": "USD",
            "cash": DEFAULT_PAPER_CASH,
            "equity": DEFAULT_PAPER_CASH,
            "net_liq": DEFAULT_PAPER_CASH,
            "buying_power": DEFAULT_PAPER_CASH * 4,
            "day_trade_bp": DEFAULT_PAPER_CASH * 4,
        },
    )
    return bal


def _recompute_balance(user, account_key: str) -> PaperBalance:
    bal = _ensure_balance(user, account_key)
    positions = PaperPosition.objects.filter(user=user, account_key=account_key)
    total_mv = sum((p.market_value for p in positions), Decimal("0"))
    bal.net_liq = (bal.cash or Decimal("0")) + total_mv
    bal.equity = bal.net_liq
    bal.buying_power = bal.net_liq * 4
    bal.day_trade_bp = bal.net_liq * 4
    bal.save(update_fields=["net_liq", "equity", "buying_power", "day_trade_bp", "updated_at"])
    return bal


@api_view(["GET"])
def paper_accounts_view(request):
    """GET /paper/accounts

    Paper has no dedicated account table yet; we expose account_key values found
    in PaperBalance (and always include a default).
    """

    user = _require_user(request)
    default_key = _default_account_key(user)

    keys = set(
        PaperBalance.objects.filter(user=user)
        .values_list("account_key", flat=True)
    )
    keys.add(default_key)

    return Response(
        {
            "accounts": [
                {
                    "account_key": key,
                    "display_name": "Paper Trading" if key == default_key else key,
                }
                for key in sorted(keys)
            ]
        }
    )


@api_view(["GET"])
def paper_balances_view(request):
    """GET /paper/balances?account_key=..."""

    user = _require_user(request)
    account_key = _resolve_account_key(request, user=user)
    bal = _ensure_balance(user, account_key)
    return Response(PaperBalanceSerializer(bal).data)


@api_view(["GET"])
def paper_positions_view(request):
    """GET /paper/positions?account_key=..."""

    user = _require_user(request)
    account_key = _resolve_account_key(request, user=user)
    qs = PaperPosition.objects.filter(user=user, account_key=account_key).order_by("symbol")
    return Response({"positions": PaperPositionSerializer(qs, many=True).data})


@api_view(["GET"])
def paper_orders_view(request):
    """GET /paper/orders?account_key=..."""

    user = _require_user(request)
    account_key = _resolve_account_key(request, user=user)
    qs = PaperOrder.objects.filter(user=user, account_key=account_key).order_by("-time_placed", "-id")
    return Response({"orders": PaperOrderSerializer(qs, many=True).data})


@dataclass
class _FillDecision:
    price: Decimal


def _get_fill_price(symbol: str) -> _FillDecision:
    mark = get_mark(symbol)
    return _FillDecision(price=(mark if mark is not None else Decimal("100")))


@api_view(["POST"])
@transaction.atomic
def paper_orders_submit_view(request):
    """POST /paper/orders/submit

    Minimal paper execution:
    - creates PaperOrder
    - creates PaperFill (single fill)
    - updates/creates PaperPosition
    - updates PaperBalance
    """

    user = _require_user(request)
    ser = PaperSubmitOrderSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    account_key = ser.validated_data["account_key"]
    symbol = ser.validated_data["symbol"].upper()
    asset_type = ser.validated_data["asset_type"].upper()
    side = ser.validated_data["side"].upper()
    quantity: Decimal = ser.validated_data["quantity"]

    bal = _ensure_balance(user, account_key)

    fill = _get_fill_price(symbol)
    price = fill.price

    notional = price * quantity
    if side == "BUY" and (bal.day_trade_bp or Decimal("0")) < notional:
        return Response({"detail": "Insufficient buying power"}, status=status.HTTP_400_BAD_REQUEST)

    order = PaperOrder.objects.create(
        user=user,
        account_key=account_key,
        client_order_id=ser.validated_data.get("client_order_id") or "",
        symbol=symbol,
        asset_type=asset_type,
        side=side,
        quantity=quantity,
        order_type=ser.validated_data.get("order_type") or "MKT",
        limit_price=ser.validated_data.get("limit_price"),
        stop_price=ser.validated_data.get("stop_price"),
        status="FILLED",
    )

    PaperFill.objects.create(
        user=user,
        account_key=account_key,
        order=order,
        exec_id="",
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        commission=ser.validated_data.get("commission") or Decimal("0"),
        fees=ser.validated_data.get("fees") or Decimal("0"),
    )

    position, _ = PaperPosition.objects.select_for_update().get_or_create(
        user=user,
        account_key=account_key,
        symbol=symbol,
        asset_type=asset_type,
        defaults={
            "description": "",
            "quantity": Decimal("0"),
            "avg_price": price,
            "mark_price": price,
            "multiplier": Decimal("1"),
        },
    )

    if side == "BUY":
        q_old = position.quantity or Decimal("0")
        q_new = q_old + quantity
        if q_old == 0:
            avg_new = price
        else:
            avg_new = (q_old * (position.avg_price or Decimal("0")) + quantity * price) / q_new
        position.quantity = q_new
        position.avg_price = avg_new
        position.mark_price = price
        position.save()

        bal.cash = (bal.cash or Decimal("0")) - (notional + (ser.validated_data.get("commission") or 0) + (ser.validated_data.get("fees") or 0))
        bal.save(update_fields=["cash", "updated_at"])

    else:  # SELL
        q_old = position.quantity or Decimal("0")
        if quantity > q_old:
            return Response({"detail": "Cannot sell more than position"}, status=status.HTTP_400_BAD_REQUEST)
        q_new = q_old - quantity
        realized = (price - (position.avg_price or Decimal("0"))) * quantity * (position.multiplier or Decimal("1"))
        position.realized_pl_day = (position.realized_pl_day or Decimal("0")) + realized
        position.realized_pl_total = (position.realized_pl_total or Decimal("0")) + realized
        position.quantity = q_new
        position.mark_price = price
        position.save()

        bal.cash = (bal.cash or Decimal("0")) + notional - (ser.validated_data.get("commission") or 0) - (ser.validated_data.get("fees") or 0)
        bal.save(update_fields=["cash", "updated_at"])

    bal = _recompute_balance(user, account_key)

    return Response(
        {
            "order": PaperOrderSerializer(order).data,
            "balance": PaperBalanceSerializer(bal).data,
        },
        status=status.HTTP_201_CREATED,
    )
