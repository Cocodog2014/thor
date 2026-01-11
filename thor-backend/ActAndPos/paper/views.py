from __future__ import annotations

from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from .engine import (
    InsufficientBuyingPower,
    InvalidPaperAccount,
    InvalidPaperOrder,
    PaperOrderParams,
    ensure_balance,
    submit_order,
)
from .models import PaperBalance, PaperOrder, PaperPosition
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

    default_key = _default_account_key(user)
    key = str(params.get("account_key") or params.get("account_id") or default_key).strip()

    # Defensive: never expose or create legacy TEST-* / non-PAPER keys.
    # Paper engine enforces PAPER-* too, but this keeps API behavior tidy.
    if not key.upper().startswith("PAPER-"):
        return default_key

    # Avoid creating arbitrary paper accounts via query params.
    if key != default_key and not PaperBalance.objects.filter(user=user, account_key=key).exists():
        return default_key

    return key


@api_view(["GET"])
def paper_accounts_view(request):
    """GET /paper/accounts

    Paper has no dedicated account table yet; we expose account_key values found
    in PaperBalance (and always include a default).
    """

    user = _require_user(request)
    default_key = _default_account_key(user)

    keys = set(
        PaperBalance.objects.filter(user=user, account_key__istartswith="PAPER-")
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
    bal = ensure_balance(user_id=user.id, account_key=account_key)
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


@api_view(["POST"])
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

    account_key = str(ser.validated_data["account_key"]).strip()
    default_key = _default_account_key(user)
    if not account_key.upper().startswith("PAPER-"):
        account_key = default_key
    if account_key != default_key and not PaperBalance.objects.filter(user=user, account_key=account_key).exists():
        account_key = default_key

    try:
        order, _fill, _position, bal = submit_order(
            PaperOrderParams(
                user_id=user.id,
                account_key=account_key,
                symbol=ser.validated_data["symbol"],
                asset_type=ser.validated_data.get("asset_type") or "EQ",
                side=ser.validated_data["side"],
                quantity=ser.validated_data["quantity"],
                order_type=ser.validated_data.get("order_type") or "MKT",
                limit_price=ser.validated_data.get("limit_price"),
                stop_price=ser.validated_data.get("stop_price"),
                client_order_id=ser.validated_data.get("client_order_id") or "",
                commission=ser.validated_data.get("commission") or Decimal("0"),
                fees=ser.validated_data.get("fees") or Decimal("0"),
            )
        )
    except InvalidPaperAccount as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except InvalidPaperOrder as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except InsufficientBuyingPower as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"order": PaperOrderSerializer(order).data, "balance": PaperBalanceSerializer(bal).data}, status=status.HTTP_201_CREATED)
