import logging

from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from LiveData.schwab.client.trader import SchwabTraderAPI
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_balances(request, account_id):
    """Fetch balances for a specific account (path param), persist, and publish to Redis."""
    try:
        if not request.user.schwab_token:
            return JsonResponse({"error": "No Schwab account connected"}, status=404)

        api = SchwabTraderAPI(request.user)
        account_hash = api.resolve_account_hash(account_id)
        balances = api.fetch_balances(account_hash)

        if balances is None:
            return JsonResponse({"error": "Unable to fetch balances from Schwab"}, status=502)

        try:
            snapshot_payload = {
                "account_id": account_hash,
                "account_number": account_id,
                "updated_at": timezone.now().isoformat(),
                **(balances if isinstance(balances, dict) else {"balances": balances}),
            }
            live_data_redis.set_json(f"live_data:balances:{account_hash}", snapshot_payload)
            live_data_redis.publish_balance(account_hash, snapshot_payload)
        except Exception as pub_err:  # pragma: no cover
            logger.warning("Schwab balances fetched but failed to publish/set Redis: %s", pub_err)

        return JsonResponse({
            "success": True,
            "account_hash": account_hash,
            "balances": balances,
            "balances_published": True,
        })

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch balances: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)
