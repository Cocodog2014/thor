from __future__ import annotations
"""Market control country ordering and selection."""

from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES

# Order matters for east→west control flow (mirrors GlobalMarkets)
_CONTROL_ORDER = [
	"Japan",
	"China",
	"India",
	"Germany",
	"United Kingdom",
	"Pre_USA",
	"USA",
	"Canada",
	"Mexico",
]

# Preserve east→west ordering while deriving from the canonical allowed set.
CONTROL_COUNTRIES = [c for c in _CONTROL_ORDER if c in ALLOWED_CONTROL_COUNTRIES]

__all__ = ["CONTROL_COUNTRIES"]