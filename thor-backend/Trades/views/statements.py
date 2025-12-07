from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.models import Position
from ActAndPos.serializers import AccountSummarySerializer
from ActAndPos.views.accounts import get_active_account

from ..models import Trade
from ..serializers import TradeSerializer

MAX_RANGE_DAYS = 370


def _resolve_date_range(
    today: date,
    days_back_param: str | None,
    from_param: str | None,
    to_param: str | None,
) -> Tuple[date, date]:
    """Normalize query params into an inclusive date range."""

    if days_back_param and not (from_param or to_param):
        try:
            days_back = int(days_back_param)
        except ValueError as exc:
            raise ValueError("days_back must be an integer.") from exc

        days_back = max(1, min(days_back, MAX_RANGE_DAYS))
        start = today - timedelta(days=days_back - 1)
        return start, today

    if from_param or to_param:
        if not (from_param and to_param):
            raise ValueError("Both from and to parameters are required.")

        start = parse_date(from_param)
        end = parse_date(to_param)
        if start is None or end is None:
            raise ValueError("from/to must be valid dates (YYYY-MM-DD).")

        if start > end:
            start, end = end, start

        if (end - start).days >= MAX_RANGE_DAYS:
            start = end - timedelta(days=MAX_RANGE_DAYS - 1)

        return start, end

    return today, today


def _as_str(value) -> str:
    return "" if value is None else str(value)


def _format_percent(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return str(value)


@api_view(["GET"])
def account_statement_view(request):
    """Aggregate account snapshot + trade history for Account Statements."""

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    today = timezone.localdate()
    days_back_param = request.query_params.get("days_back")
    from_param = request.query_params.get("from")
    to_param = request.query_params.get("to")

    try:
        start_date, end_date = _resolve_date_range(today, days_back_param, from_param, to_param)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    trades_qs = Trade.objects.filter(
        account=account,
        exec_time__date__gte=start_date,
        exec_time__date__lte=end_date,
    ).order_by("-exec_time")
    trades_data = TradeSerializer(trades_qs, many=True).data

    positions_qs = Position.objects.filter(account=account).order_by("symbol")

    equities_rows = [
        {
            "id": str(position.pk),
            "symbol": position.symbol,
            "description": position.description or "",
            "qty": _as_str(position.quantity),
            "tradePrice": _as_str(position.avg_price),
            "mark": _as_str(position.mark_price),
            "markValue": _as_str(position.market_value),
        }
        for position in positions_qs
    ]

    pnl_rows = [
        {
            "id": f"pnl-{position.pk}",
            "symbol": position.symbol,
            "description": position.description or "",
            "plOpen": _as_str(position.unrealized_pl),
            "plPct": _format_percent(position.pl_percent),
            "plDay": _as_str(position.realized_pl_day),
            "plYtd": _as_str(position.realized_pl_open),
        }
        for position in positions_qs
    ]

    account_summary = AccountSummarySerializer(account).data

    summary_rows = [
        {"id": "net_liq", "metric": "Net Liquidating Value", "value": _as_str(account.net_liq)},
        {"id": "cash", "metric": "Cash", "value": _as_str(account.cash)},
        {
            "id": "stock_bp",
            "metric": "Stock Buying Power",
            "value": _as_str(account.stock_buying_power),
        },
        {
            "id": "option_bp",
            "metric": "Option Buying Power",
            "value": _as_str(account.option_buying_power),
        },
        {
            "id": "dt_bp",
            "metric": "Day Trading Buying Power",
            "value": _as_str(account.day_trading_buying_power),
        },
    ]

    return Response(
        {
            "account": account_summary,
            "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
            "cashSweep": [],
            "futuresCash": [],
            "equities": equities_rows,
            "pnlBySymbol": pnl_rows,
            "trades": trades_data,
            "summary": summary_rows,
        }
    )
