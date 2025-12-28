"""Compatibility shim importing Schwab refresh view from api package."""

from LiveData.schwab.api.refresh import refresh_access_token

__all__ = ["refresh_access_token"]
