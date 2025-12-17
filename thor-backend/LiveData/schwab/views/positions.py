import logging
from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..services import SchwabTraderAPI
from LiveData.shared.redis_client import live_data_redis

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

        # Snapshot positions to Redis for downstream consumers (UI + EOD snapshot)
        try:
            snapshot_payload = {
                "account_id": resolved_hash,
                "account_number": account_id,
                "updated_at": timezone.now().isoformat(),
                "positions": positions,
            }
            live_data_redis.set_json(f"live_data:positions:{resolved_hash}", snapshot_payload)

            # Also publish each position entry for subscribers (best-effort)
            if isinstance(positions, list):
                for pos in positions:
                    if isinstance(pos, dict):
                        live_data_redis.publish_position(resolved_hash, {**pos, "updated_at": snapshot_payload["updated_at"]})
        except Exception as pub_err:  # pragma: no cover
            logger.warning("Schwab positions fetched but failed to publish/set Redis: %s", pub_err)

        return JsonResponse({
            "success": True,
            "message": f"Positions published to Redis for account {resolved_hash}",
            "account_hash": resolved_hash,
            "positions": positions,
            "positions_published": True,
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
