import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from LiveData.schwab.client.tokens import exchange_code_for_tokens, get_token_expiry
from LiveData.schwab.models import BrokerConnection

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def oauth_start(request):
    """Start Schwab OAuth flow and return the authorization URL."""
    raw_client_id = getattr(settings, "SCHWAB_CLIENT_ID", None)
    redirect_uri = getattr(settings, "SCHWAB_REDIRECT_URI", None)

    if not raw_client_id or not redirect_uri:
        return JsonResponse({
            "error": "Schwab OAuth not configured",
            "message": "Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI in settings",
        }, status=500)

    client_id_for_auth = raw_client_id
    auth_url = "https://api.schwabapi.com/v1/oauth/authorize"

    params = {
        "client_id": client_id_for_auth,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "api",
    }

    oauth_url = f"{auth_url}?{urlencode(params)}"

    user = request.user
    if str(getattr(user, "email", "")).lower().strip() != "admin@360edu.org":
        logger.warning("Schwab OAuth start blocked for non-admin user: %s", user)
        return JsonResponse({
            "error": "Unauthorized user for Schwab OAuth",
            "detail": "Please log in as admin@360edu.org to connect Schwab.",
        }, status=403)

    logger.info("Starting Schwab OAuth for user %s", user.username)
    logger.info("Raw client_id: %s", raw_client_id)
    logger.info("Client_id for auth: %s", client_id_for_auth)
    logger.info("Redirect URI: %s", redirect_uri)
    logger.info("Auth URL: %s", oauth_url)

    return JsonResponse({"auth_url": oauth_url})


@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def oauth_callback(request):
    """Handle OAuth callback from Schwab and persist tokens to BrokerConnection."""
    user = request.user if request.user.is_authenticated else None
    if user is None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact="admin@360edu.org")
        except User.DoesNotExist:
            logger.error("Schwab OAuth callback: admin@360edu.org user missing")
            return JsonResponse({
                "error": "Admin user not found",
                "detail": "Create admin@360edu.org to store Schwab tokens.",
            }, status=500)

    auth_code = request.GET.get("code")
    if not auth_code:
        return JsonResponse({"error": "No authorization code provided"}, status=400)

    try:
        token_data = exchange_code_for_tokens(auth_code)

        BrokerConnection.objects.update_or_create(
            user=user,
            broker=BrokerConnection.BROKER_SCHWAB,
            defaults={
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "access_expires_at": get_token_expiry(token_data["expires_in"]),
            },
        )

        logger.info("Successfully connected Schwab account for %s", getattr(user, "username", "(anonymous)"))

        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "https://dev-thor.360edu.org").rstrip("/")
        params = urlencode({"broker": "schwab", "status": "connected"})
        return redirect(f"{frontend_base}/?{params}")

    except Exception as exc:  # noqa: BLE001
        logger.error("OAuth callback failed: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)
