"""GlobalMarkets API views."""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from GlobalMarkets.models import Market
from GlobalMarkets.services import compute_market_status


def _fmt_time(t) -> Optional[str]:
    if not t:
        return None
    # Frontend expects HH:mm:ss
    return t.strftime("%H:%M:%S")


def _fmt_dt(dt) -> Optional[str]:
    if not dt:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return None


@api_view(['GET'])
def markets(request: HttpRequest):
    """Fetch markets with status + next transition.

    This endpoint is intentionally lightweight but UI-friendly.
    """

    now = timezone.now()

    markets_list = []
    for market in Market.objects.all().order_by("sort_order", "name", "id"):
        computed = compute_market_status(market, now_utc=now)
        markets_list.append(
            {
                "id": market.id,
                "key": market.key,
                # Keep both "name" and "display_name" for frontend convenience/back-compat.
                "name": market.name,
                "display_name": market.name,
                "timezone_name": market.timezone_name,
                "market_open_time": _fmt_time(getattr(market, "open_time", None)),
                "market_close_time": _fmt_time(getattr(market, "close_time", None)),
                "is_active": market.is_active,
                "sort_order": market.sort_order,
                # Computed status is always current even if persisted status is stale.
                "status": computed.status,
                "status_changed_at": _fmt_dt(market.status_changed_at),
                "next_transition_utc": _fmt_dt(computed.next_transition_utc),
            }
        )

    return Response(markets_list, status=status.HTTP_200_OK)
