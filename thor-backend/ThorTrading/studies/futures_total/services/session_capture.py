from __future__ import annotations

import logging
from typing import Any, Dict

from GlobalMarkets.models.market import Market
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketSession import MarketSession
from GlobalMarkets.services.normalize import normalize_country_code
from ThorTrading.services.sessions.metrics import MarketCloseMetric, MarketRangeMetric
from ThorTrading.studies.futures_total.quotes import get_enriched_quotes_with_composite
from ThorTrading.studies.futures_total.services.close_capture import capture_market_close
from ThorTrading.studies.futures_total.services.open_capture import (  # re-export
    ALLOWED_SESSION_FIELDS,
    MarketOpenCaptureService,
    _market_local_date,
    capture_market_open,
    check_for_market_opens_and_capture,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Study-facing stable entry points
# -----------------------------------------------------------------------------
def capture_open_for_market(market: Market, *, session_number: int | None = None):
    """Futures Total study: create MarketSession rows at market open."""
    return capture_market_open(market, session_number=session_number)


def capture_close_for_country(country: str, *, force: bool = False):
    """Futures Total study: populate close metrics for latest session."""
    return capture_market_close(country, force=force)


__all__ = [
    "ALLOWED_SESSION_FIELDS",
    "MarketOpenCaptureService",
    "check_for_market_opens_and_capture",
    "capture_market_open",
    "capture_market_close",
    "capture_open_for_market",
    "capture_close_for_country",
    "_market_local_date",
]

