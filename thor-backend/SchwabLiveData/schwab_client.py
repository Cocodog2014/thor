"""
Minimal Schwab API client scaffold to prepare for real integration.

This client encapsulates OAuth configuration placeholders and exposes
health/configuration checks so the app can report readiness without
calling the real API yet. When credentials and permissions are granted,
implement token management and REST requests here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import os
import urllib.parse
from decouple import config as dconfig


class SchwabApiClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Helper to resolve config in order of precedence: explicit config -> OS env -> .env via decouple
        def get(name: str, default: Optional[str] = None) -> Optional[str]:
            return (
                self.config.get(name.lower())
                or os.getenv(name)
                or dconfig(name, default=default)
            )

        self.client_id = get("SCHWAB_CLIENT_ID")
        self.client_secret = get("SCHWAB_CLIENT_SECRET")
        self.base_url = get("SCHWAB_BASE_URL", "https://api.schwabapi.com")
        scopes_raw = get("SCHWAB_SCOPES", "read")
        self.scopes = scopes_raw.split(",") if isinstance(scopes_raw, str) else scopes_raw
        self.redirect_uri = get("SCHWAB_REDIRECT_URI")
        self.auth_url = get("SCHWAB_AUTH_URL") or urllib.parse.urljoin(self.base_url + "/", "oauth2/authorize")
        self.token_url = get("SCHWAB_TOKEN_URL") or urllib.parse.urljoin(self.base_url + "/", "oauth2/token")
        # Placeholders for future token handling
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def health(self) -> Dict[str, Any]:
        return {
            "status": "configured" if self.configured() else "not_configured",
            "configured": self.configured(),
            "auth": {
                "client_id": bool(self.client_id),
                "client_secret": bool(self.client_secret),
                "redirect_uri": bool(self.redirect_uri),
                "scopes": self.scopes,
            },
            "oauth": {
                "auth_url": self.auth_url,
                "token_url": self.token_url,
            },
        }

    def build_authorization_url(self, state: Optional[str] = None, extra_params: Optional[Dict[str, str]] = None) -> str:
        """Construct OAuth2 authorization URL.

        Schwab typically requires the client_id, redirect_uri, response_type, and scopes.
        We pass scopes as a space-delimited string if provided as list.
        """
        if not self.configured():
            raise RuntimeError("Schwab client not configured: set SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET, SCHWAB_REDIRECT_URI")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes) if isinstance(self.scopes, (list, tuple)) else str(self.scopes),
        }
        if state:
            params["state"] = state
        if extra_params:
            params.update(extra_params)
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    # def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
    #     """TODO: Implement OAuth token exchange when ready.
    #     Requires 'requests' and specific Schwab OAuth details.
    #     """
    #     raise NotImplementedError

    # def get_quotes(self, symbols: list[str]) -> dict:
    #     """TODO: Implement when API access is granted."""
    #     raise NotImplementedError
