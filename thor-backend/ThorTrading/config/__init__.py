from __future__ import annotations
"""Configuration package for ThorTrading."""
try:
	# Prefer real symbol helpers when present.
	from ThorTrading.config.symbols import (  # type: ignore
		get_active_symbols,
		get_ribbon_symbols,
		clear_symbol_caches,
	)
except ModuleNotFoundError:
	# Symbols module intentionally removed; provide safe fallbacks.
	def get_active_symbols(country=None):
		return []

	def get_ribbon_symbols(country=None):
		return []

	def clear_symbol_caches():
		return None

from ThorTrading.config.markets import get_control_countries

__all__ = [
	"get_active_symbols",
	"get_ribbon_symbols",
	"clear_symbol_caches",
	"get_control_countries",
]