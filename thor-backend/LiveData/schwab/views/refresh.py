import logging
import time

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..tokens import ensure_valid_access_token

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_access_token(request):
    """Force a Schwab token refresh for the authenticated user."""
    try:
        connection = getattr(request.user, "schwab_token", None)
        if not connection:
            return JsonResponse({"success": False, "error": "No Schwab account connected"}, status=404)

        refreshed = ensure_valid_access_token(connection, force_refresh=True)
        expires_at = int(refreshed.access_expires_at or 0)
        expires_in = max(0, expires_at - int(time.time()))
        return JsonResponse({
            "success": True,
            "ok": True,
            "expires_at": expires_at,
            "expires_in": expires_in,
        })
    except Exception as exc:
        logger.error("Manual Schwab refresh failed: %s", exc, exc_info=True)
        return JsonResponse({"success": False, "error": str(exc)}, status=500)
