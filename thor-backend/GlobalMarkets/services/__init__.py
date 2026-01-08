"""GlobalMarkets services package (minimal shim).
Exports compute_market_status lazily to avoid early model imports during app setup.
"""

from importlib import import_module
from typing import Any

__all__ = ["compute_market_status"]


def compute_market_status(*args: Any, **kwargs: Any):
	"""Lazy wrapper to defer model import until first use."""
	impl = import_module("GlobalMarkets.services.market_clock").compute_market_status
	return impl(*args, **kwargs)
