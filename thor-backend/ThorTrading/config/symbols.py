"""Futures symbol configuration and mappings."""

FUTURES_SYMBOLS = [
	"YM",
	"ES",
	"NQ",
	"RTY",
	"CL",
	"SI",
	"HG",
	"GC",
	"VX",
	"DX",
	"ZB",
]

# Mapping from canonical symbol to Redis key (or other external feed key)
REDIS_SYMBOL_MAP = {
	"DX": "$DXY",  # Dollar Index in Redis/Excel
}

# Comprehensive normalization: any alias/external variant → canonical symbol
SYMBOL_NORMALIZE_MAP = {
	# Russell
	"RT": "RTY",
	"RTY": "RTY",
	# Bond
	"30YrBond": "ZB",
	"30Yr T-BOND": "ZB",
	"T-BOND": "ZB",
	"ZB": "ZB",
	# Dollar index variants
	"$DXY": "DX",
	"DXY": "DX",
	"USDX": "DX",
	"DX": "DX",
}

__all__ = [
	"FUTURES_SYMBOLS",
	"REDIS_SYMBOL_MAP",
	"SYMBOL_NORMALIZE_MAP",
]