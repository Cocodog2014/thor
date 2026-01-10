import logging
import re

from typing import Optional

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Position
from ..serializers import AccountSummarySerializer, PositionSerializer
from .accounts import get_active_account

logger = logging.getLogger(__name__)


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _maybe_refresh_schwab_positions_and_balances(*, request, account) -> None:
    """Best-effort refresh for SCHWAB accounts.

    This keeps ActAndPos in sync even if no external poller is running.
    Guarded by a short Redis cooldown to avoid hammering Schwab on rapid UI polls.
    """

    if getattr(account, "broker", None) != "SCHWAB":
        return

    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    force = _truthy(params.get("refresh"))

    broker_account_id = str(getattr(account, "broker_account_id", "") or "").strip()
    account_number = str(getattr(account, "account_number", "") or "").strip()

    def _looks_like_hash(value: str) -> bool:
        return bool(value and re.fullmatch(r"[A-Fa-f0-9]{32,128}", value))

    def _looks_like_account_number(value: str) -> bool:
        return bool(value and value.isdigit() and 6 <= len(value) <= 12)

    # SchwabTraderAPI accepts either, but internally it must be able to resolve to hashValue.
    # Prefer hashValue, otherwise pass accountNumber when available.
    schwab_account_id = None
    if _looks_like_hash(broker_account_id):
        schwab_account_id = broker_account_id
    elif _looks_like_account_number(account_number):
        schwab_account_id = account_number
    elif _looks_like_account_number(broker_account_id):
        schwab_account_id = broker_account_id
    else:
        schwab_account_id = broker_account_id or account_number or None

    if not schwab_account_id:
        logger.warning(
            "Schwab refresh skipped: missing account identifier (broker_account_id/account_number). account_pk=%s",
            getattr(account, "pk", None),
        )
        return

    try:
        from LiveData.shared.redis_client import live_data_redis

        cooldown_key = f"actandpos:schwab:refresh:{schwab_account_id}"
        if not force:
            acquired = live_data_redis.client.set(cooldown_key, "1", nx=True, ex=15)
            if not acquired:
                return
    except Exception:
        # If Redis is unavailable, proceed without cooldown.
        pass

    try:
        from LiveData.schwab.client.trader import SchwabTraderAPI

        api = SchwabTraderAPI(request.user)
        api.fetch_balances(schwab_account_id)
        api.fetch_positions(schwab_account_id)
    except Exception as e:
        logger.warning(
            "Schwab refresh failed. broker_account_id=%s account_number=%s chosen=%s err=%s",
            broker_account_id or "?",
            account_number or "?",
            schwab_account_id or "?",
            e,
            exc_info=True,
        )
        return

    try:
        account.refresh_from_db()
    except Exception:
        pass


@api_view(["GET"])
def positions_view(request):
    """GET /api/positions?account_id=123 – current positions plus account summary."""

    account = get_active_account(request)

    _maybe_refresh_schwab_positions_and_balances(request=request, account=account)

    positions = Position.objects.filter(account=account).order_by("symbol")

    return Response(
        {
            "account": AccountSummarySerializer(account).data,
            "positions": PositionSerializer(positions, many=True).data,
        }
    )
