from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.live.models import LiveOrder, LivePosition
from ActAndPos.paper.models import PaperOrder, PaperPosition
from ActAndPos.views.accounts import get_active_account, serialize_active_account

from .positions import _serialize_position


@api_view(["GET"])
def activity_today_view(request):
    """GET /actandpos/activity/today?account_id=123 – intraday order + position snapshot."""

    account = get_active_account(request)

    account_summary = serialize_active_account(request=request, account=account)

    today = timezone.localdate()

    def _as_str(value: Any) -> str:
        return "" if value is None else str(value)

    def _classify_status(status: str) -> str:
        s = str(status or "").upper()
        if s in {"FILLED", "EXECUTED"}:
            return "FILLED"
        if s in {"CANCELED", "CANCELLED"} or s.startswith("CANCEL"):
            return "CANCELED"
        return "WORKING"

    def _serialize_order(
        *,
        pk: int,
        symbol: str,
        asset_type: str,
        side: str,
        quantity: Decimal,
        order_type: str,
        limit_price,
        stop_price,
        status: str,
        time_placed,
        time_last_update,
        time_filled=None,
        time_canceled=None,
    ) -> dict:
        return {
            "id": pk,
            "symbol": symbol,
            "asset_type": asset_type,
            "side": side,
            "quantity": _as_str(quantity),
            "order_type": order_type,
            "limit_price": _as_str(limit_price) if limit_price is not None else None,
            "stop_price": _as_str(stop_price) if stop_price is not None else None,
            "status": status,
            "time_placed": time_placed.isoformat() if time_placed else timezone.now().isoformat(),
            "time_last_update": time_last_update.isoformat() if time_last_update else timezone.now().isoformat(),
            "time_filled": time_filled.isoformat() if time_filled else None,
            "time_canceled": time_canceled.isoformat() if time_canceled else None,
        }

    working_orders: list[dict] = []
    filled_orders: list[dict] = []
    canceled_orders: list[dict] = []

    if getattr(account, "broker", None) == "PAPER":
        base_qs = PaperOrder.objects.filter(
            user=account.user,
            account_key=str(account.broker_account_id),
            time_placed__date=today,
        ).order_by("-time_placed")

        for o in base_qs:
            bucket = _classify_status(o.status)
            row = _serialize_order(
                pk=o.pk,
                symbol=str(o.symbol or "").upper(),
                asset_type=str(o.asset_type or "EQ").upper(),
                side=str(o.side or "BUY").upper(),
                quantity=o.quantity,
                order_type=str(o.order_type or "MKT"),
                limit_price=o.limit_price,
                stop_price=o.stop_price,
                status=str(o.status or "WORKING").upper(),
                time_placed=o.time_placed,
                time_last_update=o.time_last_update,
                time_filled=None,
                time_canceled=None,
            )
            if bucket == "FILLED":
                filled_orders.append(row)
            elif bucket == "CANCELED":
                canceled_orders.append(row)
            else:
                working_orders.append(row)

        positions_qs = PaperPosition.objects.filter(
            user=account.user,
            account_key=str(account.broker_account_id),
        ).order_by("symbol")

        positions_payload = [
            _serialize_position(
                pk=p.pk,
                symbol=str(p.symbol or "").upper(),
                description=p.description or "",
                asset_type=str(p.asset_type or "EQ").upper(),
                quantity=p.quantity,
                avg_price=p.avg_price,
                mark_price=p.mark_price,
                multiplier=p.multiplier,
                realized_pl_open=p.realized_pl_total,
                realized_pl_day=p.realized_pl_day,
                currency=p.currency or "USD",
            )
            for p in positions_qs
        ]
    else:
        base_qs = LiveOrder.objects.filter(
            user=account.user,
            broker=str(account.broker),
            broker_account_id=str(account.broker_account_id),
            time_placed__date=today,
        ).order_by("-time_placed")

        for o in base_qs:
            bucket = _classify_status(o.status)
            row = _serialize_order(
                pk=o.pk,
                symbol=str(o.symbol or "").upper(),
                asset_type=str(o.asset_type or "EQ").upper(),
                side=str(o.side or "BUY").upper(),
                quantity=o.quantity,
                order_type=str(o.order_type or "MKT"),
                limit_price=o.limit_price,
                stop_price=o.stop_price,
                status=str(o.status or "WORKING").upper(),
                time_placed=o.time_placed,
                time_last_update=o.time_last_update,
                time_filled=None,
                time_canceled=None,
            )
            if bucket == "FILLED":
                filled_orders.append(row)
            elif bucket == "CANCELED":
                canceled_orders.append(row)
            else:
                working_orders.append(row)

        positions_qs = LivePosition.objects.filter(
            user=account.user,
            broker=str(account.broker),
            broker_account_id=str(account.broker_account_id),
        ).order_by("symbol")
        positions_payload = [
            _serialize_position(
                pk=p.pk,
                symbol=str(p.symbol or "").upper(),
                description=p.description or "",
                asset_type=str(p.asset_type or "EQ").upper(),
                quantity=p.quantity,
                avg_price=p.avg_price,
                mark_price=p.mark_price,
                multiplier=p.multiplier,
                realized_pl_open=p.broker_pl_ytd,
                realized_pl_day=p.broker_pl_day,
                currency=p.currency or "USD",
            )
            for p in positions_qs
        ]

    return Response(
        {
            "account": account_summary,
            "working_orders": working_orders,
            "filled_orders": filled_orders,
            "canceled_orders": canceled_orders,
            "positions": positions_payload,
            "account_status": {
                "ok_to_trade": account_summary.get("ok_to_trade", False),
                "net_liq": account_summary.get("net_liq", "0.00"),
                "day_trading_buying_power": account_summary.get("day_trading_buying_power", "0.00"),
            },
        }
    )
