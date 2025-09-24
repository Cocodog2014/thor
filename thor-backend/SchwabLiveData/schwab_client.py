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


class SchwabApiClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.client_id = self.config.get("client_id") or os.getenv("SCHWAB_CLIENT_ID")
        self.client_secret = self.config.get("client_secret") or os.getenv("SCHWAB_CLIENT_SECRET")
        self.base_url = self.config.get("base_url") or os.getenv("SCHWAB_BASE_URL", "https://api.schwabapi.com")
        self.scopes = self.config.get("scopes") or os.getenv("SCHWAB_SCOPES", "read").split(",")
        self.redirect_uri = self.config.get("redirect_uri") or os.getenv("SCHWAB_REDIRECT_URI")
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
        }

    # def get_quotes(self, symbols: list[str]) -> dict:
    #     """TODO: Implement when API access is granted."""
    #     raise NotImplementedError
