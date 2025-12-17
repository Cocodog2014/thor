import logging
import time

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import BrokerConnection

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def schwab_health(request):
    """Read-only Schwab health endpoint (no outbound Schwab calls)."""
    connection = getattr(request.user, 'schwab_token', None)

    if not connection:
        return Response({
            "connected": False,
            "broker": BrokerConnection.BROKER_SCHWAB,
            "approval_state": "not_connected",
            "last_error": None,
        })

    now = int(time.time())
    expires_at = int(connection.access_expires_at or 0)
    seconds_until_expiry = max(0, expires_at - now)
    token_expired = now >= expires_at

    approval_state = "trading_enabled" if connection.trading_enabled else "read_only"

    return Response({
        "connected": not token_expired,
        "broker": connection.broker,
        "token_expired": token_expired,
        "expires_at": expires_at,
        "seconds_until_expiry": seconds_until_expiry,
        "trading_enabled": connection.trading_enabled,
        "approval_state": approval_state,
        "last_error": None,
    })
