"""
Schwab OAuth 2.0 helper functions.

Handles token exchange and refresh flows for Schwab API authentication.
"""

import base64
import time
import logging
import urllib.parse
from typing import Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _default_expiry_buffer() -> int:
    try:
        return int(getattr(settings, "SCHWAB_TOKEN_EXPIRY_BUFFER", 60))
    except Exception:
        return 60


_EXPIRY_BUFFER_SECONDS = _default_expiry_buffer()


def _get_base_token_url() -> str:
    """
    Base URL for Schwab OAuth token endpoint.

    Can be overridden via SCHWAB_BASE_URL in settings/.env, otherwise
    defaults to the official Schwab API host.
    """
    base = getattr(settings, "SCHWAB_BASE_URL", "https://api.schwabapi.com")
    # Ensure no trailing slash
    return base.rstrip("/") + "/v1/oauth/token"


def _build_basic_auth_header() -> str:
    """
    Build the HTTP Basic Authorization header value for client_id:client_secret.
    """
    client_id = getattr(settings, "SCHWAB_CLIENT_ID", None)
    client_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)

    if not client_id or not client_secret:
        raise RuntimeError("SCHWAB_CLIENT_ID / SCHWAB_CLIENT_SECRET not configured")

    raw = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(raw.encode("ascii")).decode("ascii")
    return f"Basic {encoded}"


def exchange_code_for_tokens(auth_code: str) -> Dict[str, any]:
    """
    Exchange OAuth authorization code for access/refresh tokens.

    Args:
        auth_code: Authorization code from OAuth callback (possibly URL-encoded)

    Returns:
        Dict with at least: access_token, refresh_token, expires_in, token_type, scope, id_token
    """
    # Schwab docs: the code may contain %40, must be URL-decoded to '@'
    decoded_code = urllib.parse.unquote(auth_code or "")

    token_url = _get_base_token_url()
    redirect_uri = getattr(settings, "SCHWAB_REDIRECT_URI", None)

    if not redirect_uri:
        raise RuntimeError("SCHWAB_REDIRECT_URI not configured")

    headers = {
        "Authorization": _build_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": decoded_code,
        "redirect_uri": redirect_uri,
    }

    logger.info("Schwab OAuth: exchanging authorization code for tokens")
    logger.debug(f"Token URL: {token_url}")
    logger.debug(f"Redirect URI: {redirect_uri}")

    resp = requests.post(token_url, headers=headers, data=data, timeout=20)

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if resp.status_code != 200:
        logger.error(f"Schwab token exchange failed ({resp.status_code}): {payload}")
        raise RuntimeError(
            f"Schwab token exchange failed ({resp.status_code}): {payload}"
        )

    logger.info("Schwab OAuth: token exchange successful")
    return payload


def refresh_tokens(refresh_token: str) -> Dict[str, any]:
    """
    Use refresh token to get a new access token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        Dict with new access_token, refresh_token, expires_in, token_type, scope, id_token
    """
    decoded_refresh = urllib.parse.unquote(refresh_token or "")
    token_url = _get_base_token_url()

    headers = {
        "Authorization": _build_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": decoded_refresh,
    }

    logger.info("Schwab OAuth: refreshing access token")
    logger.debug(f"Token URL: {token_url}")

    resp = requests.post(token_url, headers=headers, data=data, timeout=20)

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if resp.status_code != 200:
        logger.error(f"Schwab refresh failed ({resp.status_code}): {payload}")
        raise RuntimeError(
            f"Schwab token refresh failed ({resp.status_code}): {payload}"
        )

    logger.info("Schwab OAuth: refresh successful")
    return payload


def get_token_expiry(expires_in: int, buffer_seconds: Optional[int] = None) -> int:
    """
    Calculate Unix timestamp for when token expires.

    Args:
        expires_in: Seconds until expiration (from OAuth response)
        buffer_seconds: Seconds to subtract so we refresh a little early.

    Returns:
        Unix timestamp of expiration time
    """
    buffer = _EXPIRY_BUFFER_SECONDS if buffer_seconds is None else max(0, int(buffer_seconds))
    seconds = max(0, int(expires_in or 0) - buffer)
    return int(time.time()) + seconds


def ensure_valid_access_token(connection, buffer_seconds: Optional[int] = None):
    """Refresh Schwab tokens when the current access token is nearing expiry."""
    if not connection:
        raise RuntimeError("No Schwab connection available to refresh.")

    buffer = _EXPIRY_BUFFER_SECONDS if buffer_seconds is None else max(0, int(buffer_seconds))
    now = int(time.time())
    expires_at = int(connection.access_expires_at or 0)

    if expires_at - buffer > now:
        return connection

    payload = refresh_tokens(connection.refresh_token)
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Schwab refresh did not return an access_token")

    refresh_token_value = payload.get("refresh_token") or connection.refresh_token
    expires_in = payload.get("expires_in") or 0
    new_expiry = get_token_expiry(expires_in, buffer_seconds=buffer)

    connection.access_token = access_token
    connection.refresh_token = refresh_token_value
    connection.access_expires_at = new_expiry
    connection.save(
        update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"]
    )

    logger.info("Schwab OAuth: access token refreshed for user_id=%s", connection.user_id)
    return connection
