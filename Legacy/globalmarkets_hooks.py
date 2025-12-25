"""Legacy shim removed.

This module was a compatibility wrapper. It is intentionally disabled to avoid
dual import paths. Import from ThorTrading.GlobalMarketGate instead.
"""

raise ImportError(
	"Legacy globalmarkets_hooks has been removed. Import from ThorTrading.GlobalMarketGate.* instead."
)
