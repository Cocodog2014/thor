"""
Schwab OAuth 2.0 helper functions.

Handles token exchange and refresh flows for Schwab API authentication.
"""

import base64
import time
import logging
import urllib.parse
from typing import Dict

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


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


def get_token_expiry(expires_in: int) -> int:
    """
    Calculate Unix timestamp for when token expires.

    Args:
        expires_in: Seconds until expiration (from OAuth response)

    Returns:
        Unix timestamp of expiration time
    """
    return int(time.time()) + int(expires_in or 0)
