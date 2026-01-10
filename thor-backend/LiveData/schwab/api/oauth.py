import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from LiveData.schwab.client.tokens import exchange_code_for_tokens, get_token_expiry
from LiveData.schwab.models import BrokerConnection

logger = logging.getLogger(__name__)


def _schwab_oauth_state_signer() -> TimestampSigner:
    return TimestampSigner(salt="schwab-oauth")


def _schwab_oauth_state_max_age_seconds() -> int:
    # Keep short: this only needs to survive the redirect round-trip.
    return int(getattr(settings, "SCHWAB_OAUTH_STATE_MAX_AGE_SECONDS", 10 * 60))


def _schwab_oauth_admin_only() -> bool:
    return bool(getattr(settings, "SCHWAB_OAUTH_ADMIN_ONLY", False))


def _is_allowed_to_connect_schwab(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not _schwab_oauth_admin_only():
        return True
    # Backward-compatible “lock it down” mode.
    email = str(getattr(user, "email", "")).lower().strip()
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False) or email == "admin@360edu.org")


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

    user = request.user
    if not _is_allowed_to_connect_schwab(user):
        logger.warning("Schwab OAuth start blocked for user: %s", user)
        return JsonResponse({
            "error": "Unauthorized user for Schwab OAuth",
            "detail": "You are not allowed to connect Schwab for this account.",
        }, status=403)

    # OAuth callbacks often arrive without an authenticated session (SPA + redirect).
    # We include a signed state token so the callback can associate tokens to the correct user.
    state = _schwab_oauth_state_signer().sign(str(user.pk))

    params = {
        "client_id": client_id_for_auth,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "api",
        "state": state,
    }

    oauth_url = f"{auth_url}?{urlencode(params)}"

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
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    if user is None:
        state = request.GET.get("state")
        if state:
            signer = _schwab_oauth_state_signer()
            try:
                user_id = signer.unsign(state, max_age=_schwab_oauth_state_max_age_seconds())
                User = get_user_model()
                user = User.objects.get(pk=int(user_id))
            except (SignatureExpired, BadSignature, ValueError, TypeError) as exc:
                logger.warning("Schwab OAuth callback: invalid/expired state: %s", exc)
                user = None
            except Exception as exc:  # noqa: BLE001
                logger.error("Schwab OAuth callback: failed to resolve user from state: %s", exc)
                user = None

    if user is None:
        # Without a user we cannot safely store tokens. Force the flow to start from inside the app.
        return JsonResponse({
            "error": "Missing user context",
            "detail": "OAuth callback missing a valid state; start Schwab connect from within the app.",
        }, status=400)

    if not _is_allowed_to_connect_schwab(user):
        return JsonResponse({
            "error": "Unauthorized user for Schwab OAuth",
            "detail": "You are not allowed to connect Schwab for this account.",
        }, status=403)

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

        logger.info("Successfully connected Schwab account for user_id=%s", getattr(user, "pk", None))

        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "https://dev-thor.360edu.org").rstrip("/")
        params = urlencode({"broker": "schwab", "status": "connected"})
        return redirect(f"{frontend_base}/?{params}")

    except Exception as exc:  # noqa: BLE001
        logger.error("OAuth callback failed: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)
