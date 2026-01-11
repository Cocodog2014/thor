import logging

from decimal import Decimal
from typing import Any, Optional

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.live.models import LivePosition
from ActAndPos.paper.models import PaperPosition
from ActAndPos.serializers import AccountSummarySerializer

from .accounts import get_active_account

logger = logging.getLogger(__name__)


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _calc_unrealized_pl(*, qty: Decimal, avg: Decimal, mark: Decimal, multiplier: Decimal) -> Decimal:
    return (mark - avg) * qty * (multiplier or Decimal("1"))


def _calc_pl_percent(*, qty: Decimal, avg: Decimal, unrealized_pl: Decimal, multiplier: Decimal) -> Decimal:
    cost = qty * avg * (multiplier or Decimal("1"))
    if not cost:
        return Decimal("0")
    try:
        return (unrealized_pl / abs(cost)) * Decimal("100")
    except Exception:
        return Decimal("0")


def _serialize_position(
    *,
    pk: int,
    symbol: str,
    description: str,
    asset_type: str,
    quantity: Decimal,
    avg_price: Decimal,
    mark_price: Decimal,
    multiplier: Decimal,
    realized_pl_open: Decimal,
    realized_pl_day: Decimal,
    currency: str,
) -> dict:
    market_value = quantity * mark_price * (multiplier or Decimal("1"))
    unrealized_pl = _calc_unrealized_pl(qty=quantity, avg=avg_price, mark=mark_price, multiplier=multiplier)
    pl_percent = _calc_pl_percent(qty=quantity, avg=avg_price, unrealized_pl=unrealized_pl, multiplier=multiplier)

    return {
        "id": pk,
        "symbol": symbol,
        "description": description or "",
        "asset_type": asset_type,
        "quantity": _as_str(quantity),
        "avg_price": _as_str(avg_price),
        "mark_price": _as_str(mark_price),
        "market_value": _as_str(market_value),
        "unrealized_pl": _as_str(unrealized_pl),
        "pl_percent": _as_str(pl_percent),
        "realized_pl_open": _as_str(realized_pl_open),
        "realized_pl_day": _as_str(realized_pl_day),
        "currency": currency or "USD",
    }


def _maybe_refresh_schwab(*, request, account) -> None:
    if getattr(account, "broker", None) != "SCHWAB":
        return

    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    if not _truthy(params.get("refresh")):
        return

    try:
        from ActAndPos.live.brokers.schwab.sync import sync_schwab_account

        sync_schwab_account(
            user=request.user,
            broker_account_id=str(account.broker_account_id),
            include_orders=False,
            publish_ws=True,
        )
    except Exception:
        logger.exception("Schwab sync failed for positions refresh")


@api_view(["GET"])
def positions_view(request):
    """GET /api/positions?account_id=123 – current positions plus account summary."""

    account = get_active_account(request)

    _maybe_refresh_schwab(request=request, account=account)

    positions_payload: list[dict] = []
    if getattr(account, "broker", None) == "PAPER":
        qs = PaperPosition.objects.filter(user=account.user, account_key=str(account.broker_account_id)).order_by(
            "symbol"
        )
        for p in qs:
            positions_payload.append(
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
            )
    else:
        qs = LivePosition.objects.filter(
            user=account.user,
            broker=str(account.broker),
            broker_account_id=str(account.broker_account_id),
        ).order_by("symbol")
        for p in qs:
            positions_payload.append(
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
            )

    return Response(
        {
            "account": AccountSummarySerializer(account).data,
            "positions": positions_payload,
        }
    )
