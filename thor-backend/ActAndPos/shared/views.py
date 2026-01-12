"""Shared cross-domain views.

Views that don't belong to paper or live specifically but serve
both domains or aggregate across them.
"""
from __future__ import annotations

from datetime import datetime, time

from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated

from ..paper.models import PaperBalance
from ..live.models import LiveBalance


def _require_user(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")
    return user


def _as_str(value) -> str:
    if value is None:
        return "0"
    return str(value)


def _money_str(value) -> str:
    """Format numbers for UI money fields.

    Frontend types currently expect strings for many numeric fields.
    We keep it simple and stable: always return a string.
    """

    if value is None:
        return "0.00"
    try:
        # Decimal, int, float all stringify fine; ensure two-decimal feel.
        from decimal import Decimal

        d = value if isinstance(value, Decimal) else Decimal(str(value))
        return f"{d:.2f}"
    except Exception:
        return str(value)


def _percent_str(value) -> str:
    if value is None:
        return "0.00"
    try:
        from decimal import Decimal

        d = value if isinstance(value, Decimal) else Decimal(str(value))
        return f"{d:.2f}"
    except Exception:
        return str(value)


def _dt_str(dt) -> str:
    if not dt:
        return timezone.now().isoformat()
    try:
        return dt.isoformat()
    except Exception:
        return timezone.now().isoformat()


def _serialize_order_for_ui(order, *, status_value: str) -> dict:
    status_upper = str(status_value or "").upper()
    time_filled = None
    time_canceled = None
    if status_upper in {"FILLED", "PARTIAL"}:
        time_filled = _dt_str(getattr(order, "time_last_update", None) or getattr(order, "time_placed", None))
    if status_upper in {"CANCELED", "CANCELLED", "REJECTED"}:
        time_canceled = _dt_str(getattr(order, "time_last_update", None) or getattr(order, "time_placed", None))

    return {
        "id": int(getattr(order, "id")),
        "symbol": str(getattr(order, "symbol", "")),
        "asset_type": str(getattr(order, "asset_type", "EQ")),
        "side": str(getattr(order, "side", "BUY")),
        "quantity": _as_str(getattr(order, "quantity", "0")),
        "order_type": str(getattr(order, "order_type", "MKT")),
        "limit_price": None if getattr(order, "limit_price", None) is None else _as_str(getattr(order, "limit_price")),
        "stop_price": None if getattr(order, "stop_price", None) is None else _as_str(getattr(order, "stop_price")),
        "status": status_upper or "WORKING",
        "time_placed": _dt_str(getattr(order, "time_placed", None)),
        "time_last_update": _dt_str(getattr(order, "time_last_update", None) or getattr(order, "time_placed", None)),
        "time_filled": time_filled,
        "time_canceled": time_canceled,
    }


def _serialize_position_for_ui(position, *, broker: str) -> dict:
    from decimal import Decimal

    qty = getattr(position, "quantity", None) or Decimal("0")
    avg = getattr(position, "avg_price", None) or Decimal("0")
    mark = getattr(position, "mark_price", None) or Decimal("0")
    multiplier = getattr(position, "multiplier", None) or Decimal("1")

    market_value = qty * mark * multiplier
    unrealized_pl = (mark - avg) * qty * multiplier
    pl_percent = Decimal("0")
    if avg and avg != 0:
        pl_percent = (mark - avg) / avg * Decimal("100")

    if str(broker).upper() == "PAPER":
        realized_open = getattr(position, "realized_pl_total", None)
        realized_day = getattr(position, "realized_pl_day", None)
    else:
        # Live positions have broker_pl_day and broker_pl_ytd.
        realized_open = getattr(position, "broker_pl_ytd", None)
        realized_day = getattr(position, "broker_pl_day", None)

    return {
        "id": int(getattr(position, "id")),
        "symbol": str(getattr(position, "symbol", "")),
        "description": str(getattr(position, "description", "")),
        "asset_type": str(getattr(position, "asset_type", "EQ")),
        "quantity": _as_str(qty),
        "avg_price": _as_str(avg),
        "mark_price": _as_str(mark),
        "market_value": _money_str(market_value),
        "unrealized_pl": _money_str(unrealized_pl),
        "pl_percent": _percent_str(pl_percent),
        "realized_pl_open": _money_str(realized_open),
        "realized_pl_day": _money_str(realized_day),
        "currency": str(getattr(position, "currency", "USD")),
    }


@api_view(["GET"])
def account_balance_view(request):
    """GET /api/accounts/balance/
    
    Aggregates both paper and live balances for the authenticated user.
    Respects ?account_id=... and returns the balance for that account.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")

    # Resolve active account (paper/live) using the same rules as ActAndPos.
    from ActAndPos.shared.accounts import get_active_account

    acct = get_active_account(request)
    now_iso = timezone.now().isoformat()

    if str(acct.broker).upper() == "PAPER":
        bal = PaperBalance.objects.filter(user=user, account_key=str(acct.broker_account_id)).order_by("-updated_at").first()
        if bal is None:
            # Ensure a default paper balance exists (best-effort).
            try:
                from ActAndPos.shared.accounts import resolve_account_for_user

                resolve_account_for_user(user=user, account_id=None)
            except Exception:
                pass
            bal = PaperBalance.objects.filter(user=user, account_key=str(acct.broker_account_id)).order_by("-updated_at").first()

        if bal is None:
            return Response({"detail": "Balance not found"}, status=404)

        return Response(
            {
                "account_id": str(bal.account_key),
                "net_liquidation": float(bal.net_liq or 0),
                "equity": float(bal.equity or 0),
                "cash": float(bal.cash or 0),
                "buying_power": float(bal.buying_power or 0),
                "day_trade_bp": float(bal.day_trade_bp or 0),
                "updated_at": bal.updated_at.isoformat() if bal.updated_at else now_iso,
                "source": "paper",
            }
        )

    bal = LiveBalance.objects.filter(
        user=user,
        broker=str(acct.broker or "SCHWAB").upper(),
        broker_account_id=str(acct.broker_account_id),
    ).order_by("-updated_at").first()

    if bal is None:
        return Response({"detail": "Balance not found"}, status=404)

    return Response(
        {
            "account_id": str(bal.broker_account_id),
            "net_liquidation": float(bal.net_liq or 0),
            "equity": float(bal.equity or 0),
            "cash": float(bal.cash or 0),
            "buying_power": float(bal.stock_buying_power or 0),
            "day_trade_bp": float(bal.day_trading_buying_power or 0),
            "updated_at": bal.updated_at.isoformat() if bal.updated_at else now_iso,
            "source": "live",
        }
    )


@api_view(["GET"])
def activity_today_view(request):
    """GET /api/actandpos/activity/today?account_id=...

    Returns a unified ActivityTodayResponse shape for the selected account,
    regardless of whether it is PAPER or LIVE.
    """

    user = _require_user(request)

    from ActAndPos.shared.accounts import get_active_account, serialize_active_account

    acct = get_active_account(request)
    account_payload = serialize_active_account(request=request, account=acct)

    today = timezone.localdate()
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(today, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(today, time.max), tz)

    working_orders: list[dict] = []
    filled_orders: list[dict] = []
    canceled_orders: list[dict] = []
    positions: list[dict] = []

    if str(acct.broker).upper() == "PAPER":
        from ActAndPos.paper.models import PaperOrder, PaperPosition

        order_qs = PaperOrder.objects.filter(
            user=user,
            account_key=str(acct.broker_account_id),
            time_placed__gte=start_dt,
            time_placed__lte=end_dt,
        ).order_by("-time_placed", "-id")

        for o in order_qs:
            status_value = getattr(o, "status", "WORKING")
            payload = _serialize_order_for_ui(o, status_value=status_value)
            st = str(status_value or "").upper()
            if st in {"FILLED", "PARTIAL"}:
                filled_orders.append(payload)
            elif st in {"CANCELED", "CANCELLED", "REJECTED"}:
                canceled_orders.append(payload)
            else:
                working_orders.append(payload)

        pos_qs = PaperPosition.objects.filter(
            user=user,
            account_key=str(acct.broker_account_id),
        ).order_by("symbol")
        positions = [_serialize_position_for_ui(p, broker="PAPER") for p in pos_qs]
    else:
        from ActAndPos.live.models import LiveOrder, LivePosition

        order_qs = LiveOrder.objects.filter(
            user=user,
            broker_account_id=str(acct.broker_account_id),
        ).filter(Q(time_placed__gte=start_dt) & Q(time_placed__lte=end_dt)).order_by("-time_placed", "-id")

        for o in order_qs:
            status_value = getattr(o, "status", "WORKING")
            payload = _serialize_order_for_ui(o, status_value=status_value)
            st = str(status_value or "").upper()
            if st in {"FILLED", "PARTIAL"}:
                filled_orders.append(payload)
            elif st in {"CANCELED", "CANCELLED", "REJECTED"}:
                canceled_orders.append(payload)
            else:
                working_orders.append(payload)

        pos_qs = LivePosition.objects.filter(
            user=user,
            broker_account_id=str(acct.broker_account_id),
        ).order_by("symbol")
        positions = [_serialize_position_for_ui(p, broker=str(acct.broker)) for p in pos_qs]

    account_status = {
        "ok_to_trade": bool(account_payload.get("ok_to_trade")),
        "net_liq": account_payload.get("net_liq", "0.00"),
        "day_trading_buying_power": account_payload.get("day_trading_buying_power", "0.00"),
    }

    return Response(
        {
            "account": account_payload,
            "working_orders": working_orders,
            "filled_orders": filled_orders,
            "canceled_orders": canceled_orders,
            "positions": positions,
            "account_status": account_status,
        }
    )
