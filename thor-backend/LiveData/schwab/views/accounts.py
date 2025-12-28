"""Compatibility shim importing Schwab account views from api package."""

from LiveData.schwab.api.accounts import account_summary, list_accounts

__all__ = ["list_accounts", "account_summary"]
