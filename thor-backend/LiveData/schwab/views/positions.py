import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..services import SchwabTraderAPI

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_positions(request, account_id):
    """
    Fetch positions for a specific account (path param).
    Publishes positions to Redis for consumption by other apps.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)

        api = SchwabTraderAPI(request.user)
        resolved_hash = api.resolve_account_hash(account_id)
        positions = api.fetch_positions(resolved_hash)

        return JsonResponse({
            "success": True,
            "message": f"Positions published to Redis for account {resolved_hash}",
            "account_hash": resolved_hash,
            "positions": positions
        })

    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab positions API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error("Failed to fetch positions: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_positions(request):
    """Fetch positions by account_hash or account_number via query params."""
    try:
        if not request.user.schwab_token:
            return JsonResponse({"error": "No Schwab account connected"}, status=404)

        api = SchwabTraderAPI(request.user)
        account_number = request.query_params.get("account_number")
        account_hash_param = request.query_params.get("account_hash")
        account_id = account_number or account_hash_param

        if not account_id:
            return JsonResponse({"error": "Provide account_number or account_hash"}, status=400)

        account_hash = api.resolve_account_hash(account_id)
        positions = api.fetch_positions(account_hash)
        return JsonResponse({
            "success": True,
            "account_hash": account_hash,
            "account_number": account_number,
            "positions": positions,
        })

    except Exception as e:
        logger.exception("positions failed")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
