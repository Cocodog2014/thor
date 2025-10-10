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
import json
from pathlib import Path
import time
from datetime import datetime, timedelta, timezone
import requests


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
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None

        # Token store location (not committed): thor-backend/data/schwab_tokens.json
        base_dir = Path(__file__).resolve().parents[1]
        self.token_store = base_dir / "data" / "schwab_tokens.json"
        self._load_tokens_from_store()

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
            "tokens": {
                "present": bool(self._access_token),
                "expires_at": datetime.fromtimestamp(self._token_expires_at, tz=timezone.utc).isoformat() if self._token_expires_at else None,
                "expired": (self._token_expires_at is not None and time.time() >= self._token_expires_at),
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

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens.

        Note: Paths and exact params may vary if Schwab requires special handling.
        We use a standard OAuth2 code exchange with form-encoded body.
        """
        if not self.configured():
            raise RuntimeError("Schwab client not configured")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(self.token_url, data=payload, headers=headers, timeout=20)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = {"text": resp.text}
            raise RuntimeError(f"Token exchange failed ({resp.status_code}): {err}")

        tok = resp.json()
        self._access_token = tok.get("access_token")
        self._refresh_token = tok.get("refresh_token")
        expires_in = tok.get("expires_in")
        if isinstance(expires_in, (int, float)):
            self._token_expires_at = time.time() + float(expires_in)
        else:
            self._token_expires_at = None
        self._save_tokens_to_store(tok)

        # Return sanitized info
        out = {
            "ok": True,
            "expires_in": tok.get("expires_in"),
            "scope": tok.get("scope") or tok.get("scopes"),
            "token_type": tok.get("token_type"),
        }
        return out

    # --- Token persistence helpers (simple file-based store) ---
    def _load_tokens_from_store(self) -> None:
        try:
            if self.token_store.exists():
                with self.token_store.open("r", encoding="utf-8") as f:
                    tok = json.load(f)
                self._access_token = tok.get("access_token")
                self._refresh_token = tok.get("refresh_token")
                # Recompute expiry if present
                if tok.get("expires_at"):
                    self._token_expires_at = float(tok["expires_at"])
                elif tok.get("expires_in"):
                    self._token_expires_at = time.time() + float(tok["expires_in"]) - 60
        except Exception:
            # Ignore parsing errors; treat as no tokens
            self._access_token = None
            self._refresh_token = None
            self._token_expires_at = None

    def _save_tokens_to_store(self, tok: Dict[str, Any]) -> None:
        try:
            self.token_store.parent.mkdir(parents=True, exist_ok=True)
            # Persist only what's necessary
            to_save = {
                "access_token": tok.get("access_token"),
                "refresh_token": tok.get("refresh_token"),
                "expires_in": tok.get("expires_in"),
                "expires_at": self._token_expires_at,
                "saved_at": time.time(),
            }
            with self.token_store.open("w", encoding="utf-8") as f:
                json.dump(to_save, f)
        except Exception:
            pass

    # def get_quotes(self, symbols: list[str]) -> dict:
    #     """TODO: Implement when API access is granted."""
    #     raise NotImplementedError
