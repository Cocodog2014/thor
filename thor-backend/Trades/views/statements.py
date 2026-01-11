from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.views.accounts import get_active_account

from ActAndPos.shared.statement.service import build_statement

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

    payload = build_statement(
        user=request.user,
        account=account,
        days_back=days_back_param,
        from_param=from_param,
        to_param=to_param,
    )

    # Keep existing Trades.Trade history in response for now (UI expects it),
    # but prefer the unified source list if it contains trades.
    if not payload.get("trades"):
        trades_qs = Trade.objects.filter(
            account=account,
            exec_time__date__gte=start_date,
            exec_time__date__lte=end_date,
        ).order_by("-exec_time")
        payload["trades"] = TradeSerializer(trades_qs, many=True).data

    return Response(payload)
