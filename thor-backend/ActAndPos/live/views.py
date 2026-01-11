from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from .models import LiveBalance, LiveOrder, LivePosition
from .serializers import LiveBalanceSerializer, LiveOrderSerializer, LivePositionSerializer, LiveSubmitOrderSerializer

from .services.order_router import LiveSubmitOrderParams, submit_order

from .brokers.schwab.sync import sync_schwab_account

try:
    from LiveData.shared.redis_client import live_data_redis
except Exception:  # pragma: no cover
    live_data_redis = None  # type: ignore


def _require_user(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")
    return user


def _get_param(request, key: str) -> Optional[str]:
    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    val = params.get(key)
    return None if val in (None, "", "null") else str(val)


def _dec(value, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value if value is not None else default))
    except Exception:
        return default


def _read_redis_json(key: str) -> Optional[Dict[str, Any]]:
    if live_data_redis is None:
        return None
    client = getattr(live_data_redis, "client", None)
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception:
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


@api_view(["GET"])
def live_accounts_view(request):
    """GET /live/accounts

    For now this is derived from LiveBalance rows for the user.
    """

    user = _require_user(request)
    qs = LiveBalance.objects.filter(user=user).order_by("broker", "broker_account_id")
    accounts = [
        {
            "broker": row.broker,
            "broker_account_id": row.broker_account_id,
            "display_name": row.broker_account_id,
        }
        for row in qs
    ]
    return Response({"accounts": accounts})


@api_view(["GET"])
def live_balances_view(request):
    """GET /live/balances?broker_account_id=..."""

    user = _require_user(request)
    broker_account_id = _get_param(request, "broker_account_id")
    if not broker_account_id:
        # Return all balances (small payload, user-scoped)
        qs = LiveBalance.objects.filter(user=user).order_by("broker", "broker_account_id")
        return Response({"balances": LiveBalanceSerializer(qs, many=True).data})

    row = LiveBalance.objects.filter(user=user, broker_account_id=broker_account_id).order_by("-updated_at").first()
    if row is None:
        return Response({"detail": "Balance not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(LiveBalanceSerializer(row).data)


@api_view(["GET"])
def live_positions_view(request):
    """GET /live/positions?broker_account_id=..."""

    user = _require_user(request)
    broker_account_id = _get_param(request, "broker_account_id")
    qs = LivePosition.objects.filter(user=user)
    if broker_account_id:
        qs = qs.filter(broker_account_id=broker_account_id)
    qs = qs.order_by("symbol")
    return Response({"positions": LivePositionSerializer(qs, many=True).data})


@api_view(["GET"])
def live_orders_view(request):
    """GET /live/orders?broker_account_id=..."""

    user = _require_user(request)
    broker_account_id = _get_param(request, "broker_account_id")
    qs = LiveOrder.objects.filter(user=user)
    if broker_account_id:
        qs = qs.filter(broker_account_id=broker_account_id)
    qs = qs.order_by("-time_placed", "-id")
    return Response({"orders": LiveOrderSerializer(qs, many=True).data})


@api_view(["POST"])
def live_orders_submit_view(request):
    """POST /live/orders/submit

    Placeholder until broker adapters are wired into LiveOrder/LiveExecution.
    """

    user = _require_user(request)
    ser = LiveSubmitOrderSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        order = submit_order(
            LiveSubmitOrderParams(
                user_id=user.id,
                broker=ser.validated_data.get("broker") or "SCHWAB",
                broker_account_id=ser.validated_data["broker_account_id"],
                symbol=ser.validated_data["symbol"],
                asset_type=ser.validated_data.get("asset_type") or "EQ",
                side=ser.validated_data["side"],
                quantity=ser.validated_data["quantity"],
                order_type=ser.validated_data.get("order_type") or "MKT",
                limit_price=ser.validated_data.get("limit_price"),
                stop_price=ser.validated_data.get("stop_price"),
            )
        )
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"order": LiveOrderSerializer(order).data}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def live_refresh_view(request):
    """POST /live/refresh?broker_account_id=<hash>

    Pull latest cached Schwab snapshots from Redis (written by the poller) and
    upsert them into LiveBalance/LivePosition.
    """

    user = _require_user(request)
    broker_account_id = _get_param(request, "broker_account_id")
    if not broker_account_id:
        return Response({"detail": "broker_account_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Preferred: hit Schwab directly and upsert into Live*.
    # Fallback: if Schwab is unavailable, use last-good Redis snapshots.
    try:
        result = sync_schwab_account(
            user=user,
            broker_account_id=broker_account_id,
            include_orders=True,
            publish_ws=True,
        )
        return Response(
            {
                "broker_account_id": broker_account_id,
                "account_hash": result.account_hash,
                "refreshed_at": timezone.now().isoformat(),
                "source": "schwab",
                "balances_upserted": result.balances_upserted,
                "positions_upserted": result.positions_upserted,
                "positions_deleted": result.positions_deleted,
                "orders_upserted": result.orders_upserted,
            }
        )
    except Exception:
        # Fall back to Redis-backed refresh.
        pass

    balance_payload = _read_redis_json(f"live_data:balances:{broker_account_id}") or {}
    positions_payload = _read_redis_json(f"live_data:positions:{broker_account_id}") or {}

    # --- balance upsert -----------------------------------------------------
    if balance_payload:
        LiveBalance.objects.update_or_create(
            user=user,
            broker="SCHWAB",
            broker_account_id=broker_account_id,
            defaults={
                "currency": "USD",
                "net_liq": _dec(balance_payload.get("net_liq")),
                "cash": _dec(balance_payload.get("cash")),
                "equity": _dec(balance_payload.get("equity"), _dec(balance_payload.get("net_liq"))),
                "stock_buying_power": _dec(balance_payload.get("stock_buying_power")),
                "option_buying_power": _dec(balance_payload.get("option_buying_power")),
                "day_trading_buying_power": _dec(balance_payload.get("day_trading_buying_power")),
                "broker_payload": balance_payload,
            },
        )

    # --- positions upsert ---------------------------------------------------
    raw_positions: Iterable = positions_payload.get("positions") or []
    updated = 0
    for row in raw_positions:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue
        LivePosition.objects.update_or_create(
            user=user,
            broker="SCHWAB",
            broker_account_id=broker_account_id,
            symbol=symbol,
            asset_type=str(row.get("asset_type") or "EQ").upper(),
            defaults={
                "description": str(row.get("description") or ""),
                "quantity": _dec(row.get("quantity")),
                "avg_price": _dec(row.get("avg_price")),
                "mark_price": _dec(row.get("mark_price")),
                "broker_pl_day": _dec(row.get("broker_pl_day"), _dec(row.get("realized_pl_day"))),
                "broker_pl_ytd": _dec(row.get("broker_pl_ytd"), _dec(row.get("realized_pl_open"))),
                "multiplier": _dec(row.get("multiplier"), Decimal("1")),
                "currency": str(row.get("currency") or "USD"),
                "broker_payload": row,
            },
        )
        updated += 1

    return Response(
        {
            "broker_account_id": broker_account_id,
            "refreshed_at": timezone.now().isoformat(),
            "balance_source": "redis" if balance_payload else "none",
            "positions_source": "redis" if raw_positions else "none",
            "positions_upserted": updated,
        }
    )
