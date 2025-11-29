# FutureTrading/services/metrics/session_open.py

import logging
from decimal import Decimal
from django.db.models import F
from FutureTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


class MarketOpenMetric:
    """Populate market_open = last_price for all rows in a session."""

    @staticmethod
    def update(session_number: int) -> int:
        logger.info("MarketOpenMetric → Session %s", session_number)

        base_qs = MarketSession.objects.filter(session_number=session_number)
        open_updated = base_qs.update(market_open=F("last_price"))

        initialized_count = 0
        for session in base_qs.only(
            "id", "market_high_open", "market_low_open",
            "last_price", "market_high_pct_open", "market_low_pct_open"
        ):
            lp = session.last_price
            if lp in (None, 0):
                continue

            to_update = []
            if session.market_high_open is None:
                session.market_high_open = lp
                session.market_high_pct_open = Decimal("0")
                to_update.extend(["market_high_open", "market_high_pct_open"])
            if session.market_low_open is None:
                session.market_low_open = lp
                session.market_low_pct_open = Decimal("0")
                to_update.extend(["market_low_open", "market_low_pct_open"])

            if to_update:
                session.save(update_fields=to_update)
                initialized_count += 1

        logger.info(
            "MarketOpenMetric complete → %s open prices, %s high/low initialized (session %s)",
            open_updated, initialized_count, session_number,
        )
        return open_updated
