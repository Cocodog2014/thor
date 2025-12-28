"""Compatibility shim importing Schwab positions views from api package."""

from LiveData.schwab.api.positions import account_positions, get_positions

__all__ = ["get_positions", "account_positions"]
