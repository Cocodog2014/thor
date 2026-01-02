from __future__ import annotations

from typing import Optional


def normalize_market_key(raw: str | None) -> Optional[str]:
	"""Normalize a market key/country code using GlobalMarkets.Market as source of truth.

	Returns the canonical `Market.country` value if a matching market exists
	(case-insensitive); otherwise returns None.
	"""
	if raw is None:
		return None

	s = str(raw).strip()
	if not s:
		return None

	# Import lazily to avoid AppRegistryNotReady during Django startup.
	from GlobalMarkets.models.market import Market

	market = Market.objects.filter(country__iexact=s).only("country").first()
	return market.country if market else None


def is_known_market_key(raw: str | None, **_ignored) -> bool:
	"""Return True if `raw` normalizes to a known Market.

	Accepts extra kwargs for backward compatibility with older call sites.
	"""
	return normalize_market_key(raw) is not None


def is_known_country(raw: str | None, *, controlled: set[str]) -> bool:
	"""Signature-compatible helper for code that uses `controlled=`.

	`controlled` should contain canonical country keys.
	"""
	normalized = normalize_market_key(raw)
	if not normalized:
		return False
	return normalized in controlled or (raw in controlled if raw else False)


# Backward-friendly alias: some callers talk about "countries" rather than "market keys".
normalize_country_code = normalize_market_key


__all__ = [
	"normalize_market_key",
	"is_known_market_key",
	"is_known_country",
	"normalize_country_code",
]
