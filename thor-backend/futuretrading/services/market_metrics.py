# FutureTrading/services/market_metrics.py

"""
MarketSession metrics helpers.

Right now this only manages `market_open`:
- Copies `last_price` into `market_open` for a given session_number.
- Intended to be called right after MarketOpenCapture creates its rows.

Later we can add:
- market_high_number / market_high_percentage
- market_low_number / market_low_percentage
- market_close_number / market_close_percentage
- market_range_number / market_range_percentage
"""

import logging
from django.db.models import F
from django.utils import timezone

from FutureTrading.models.MarketSession import MarketSession


logger = logging.getLogger(__name__)


def update_market_open_for_session(session_number: int) -> int:
    """
    For all rows in the given session_number, set:

        market_open = last_price

    Returns the number of rows updated.
    """
    logger.info(
        "Updating market_open from last_price for session %s at %s",
        session_number,
        timezone.now(),
    )

    updated = (
        MarketSession.objects
        .filter(session_number=session_number)
        .update(market_open=F("last_price"))
    )

    logger.info(
        "market_open refresh complete for session %s: %s rows updated",
        session_number,
        updated,
    )
    return updated
