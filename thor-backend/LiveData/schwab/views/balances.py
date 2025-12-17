import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..services import SchwabTraderAPI

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balances(request, account_id):
    """
    Fetch balances for a specific account (path param), persist, and publish to Redis.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)

        api = SchwabTraderAPI(request.user)
        account_hash = api.resolve_account_hash(account_id)
        balances = api.fetch_balances(account_hash)

        if balances is None:
            return JsonResponse({"error": "Unable to fetch balances from Schwab"}, status=502)

        return JsonResponse({
            "success": True,
            "account_hash": account_hash,
            "balances": balances,
        })

    except Exception as e:
        logger.error("Failed to fetch balances: %s", e)
        return JsonResponse({"error": str(e)}, status=500)
