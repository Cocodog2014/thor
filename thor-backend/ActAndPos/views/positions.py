import logging

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

    force = _truthy(request.query_params.get("refresh"))

    try:
        from LiveData.shared.redis_client import live_data_redis

        cooldown_key = f"actandpos:schwab:refresh:{account.broker_account_id}"
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
        api.fetch_balances(str(account.broker_account_id))
        api.fetch_positions(str(account.broker_account_id))
    except Exception as e:
        logger.warning("Schwab refresh failed for account %s: %s", getattr(account, "broker_account_id", "?"), e)
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
