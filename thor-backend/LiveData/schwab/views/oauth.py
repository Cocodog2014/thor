"""Compatibility shim importing Schwab OAuth views from api package."""

from LiveData.schwab.api.oauth import oauth_callback, oauth_start

__all__ = ["oauth_start", "oauth_callback"]
