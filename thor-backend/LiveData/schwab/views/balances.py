"""Compatibility shim importing Schwab balances view from api package."""

from LiveData.schwab.api.balances import get_balances

__all__ = ["get_balances"]
