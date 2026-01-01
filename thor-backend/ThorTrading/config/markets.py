"""Control-market configuration helpers.

Implementation remains in ThorTrading; `GlobalMarkets.config.markets` is an alias
path for callers that prefer the GlobalMarkets namespace.
"""

import logging
from typing import List, Optional

from GlobalMarkets.models.market import Market
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


def _country(m: Market) -> Optional[str]:
	raw = getattr(m, "country", None)
	return (normalize_country_code(raw) or raw) if raw else None


def _tz_sort_key(m: Market) -> tuple:
	"""Try to sort markets east->west using whatever timezone info exists on Market.

	Falls back safely if those fields don't exist.
	"""
	off_min = getattr(m, "utc_offset_minutes", None)
	if isinstance(off_min, int):
		# East (positive) first, West (negative) later -> sort by descending
		return (-off_min, _country(m) or "")

	off_hr = getattr(m, "utc_offset", None)
	if isinstance(off_hr, (int, float)):
		return (-(float(off_hr) * 60.0), _country(m) or "")

	return (0, _country(m) or "")


def get_control_markets(*, require_session_capture: bool = False) -> List[Market]:
	"""Return active control markets from the GlobalMarkets DB.

	- is_active=True always
	- optionally require enable_session_capture=True
	  (turn this on if you ONLY want markets that run the session pipeline)
	"""
	qs = Market.objects.filter(is_active=True)
	if require_session_capture:
		qs = qs.filter(enable_session_capture=True)

	markets = list(qs)
	markets.sort(key=_tz_sort_key)
	return markets


def get_control_countries(*, require_session_capture: bool = False) -> List[str]:
	"""Return normalized control country codes, ordered and de-duped."""
	countries: List[str] = []
	for m in get_control_markets(require_session_capture=require_session_capture):
		c = _country(m)
		if c:
			countries.append(c)

	seen: set[str] = set()
	ordered: List[str] = []
	for c in countries:
		if c not in seen:
			seen.add(c)
			ordered.append(c)
	return ordered


__all__ = ["get_control_markets", "get_control_countries"]
