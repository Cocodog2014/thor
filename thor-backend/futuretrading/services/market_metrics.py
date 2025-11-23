"""MarketSession metrics system.

Defines metric update helpers for intraday calculations. Keep each metric
focused so they can be composed by background monitors without overlap.

Implemented:
  - MarketOpenMetric  → copies last_price → market_open after capture
  - MarketHighMetric  → updates market_high_number / market_high_percentage

Placeholders (to implement later):
  - MarketLowMetric
  - MarketCloseMetric
  - MarketRangeMetric
"""

import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Max
from FutureTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


def _safe_decimal(val):
    if val in (None, "", " "):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


# -------------------------------------------------------------------------
# ⭐ MARKET OPEN METRIC
# -------------------------------------------------------------------------

class MarketOpenMetric:
    """Populate market_open = last_price for all rows in a session."""

    @staticmethod
    def update(session_number: int) -> int:
        logger.info("MarketOpenMetric → Session %s", session_number)
        updated = (
            MarketSession.objects
            .filter(session_number=session_number)
            .update(market_open=F("last_price"))
        )
        logger.info(
            "MarketOpenMetric complete → %s rows updated (session %s)",
            updated, session_number
        )
        return updated


# -------------------------------------------------------------------------
# ⭐ MARKET HIGH METRIC
# -------------------------------------------------------------------------

class MarketHighMetric:
    """Track intraday high and percent move from open for a country.

    Repeated calls during an active market update the latest session's rows.
    """

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows) -> int:
        if not enriched_rows:
            return 0

        logger.info("MarketHighMetric → Updating %s", country)
        latest_session = (
            MarketSession.objects
            .filter(country=country)
            .aggregate(max_session=Max("session_number"))
            .get("max_session")
        )
        if latest_session is None:
            logger.info("MarketHighMetric → No sessions for %s", country)
            return 0

        updated_count = 0
        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")
            if not symbol:
                continue
            future = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(country=country, future=future, session_number=latest_session)
                .first()
            )
            if not session or session.market_open is None:
                continue

            if session.market_high_number is None or last_price > session.market_high_number:
                session.market_high_number = last_price
                try:
                    move = last_price - session.market_open
                    pct = (move / session.market_open) * Decimal("100") if session.market_open != 0 else None
                except (InvalidOperation, ZeroDivisionError):
                    pct = None
                session.market_high_percentage = pct
                session.save(update_fields=["market_high_number", "market_high_percentage"])
                updated_count += 1

        logger.info(
            "MarketHighMetric complete → %s updated (country=%s session=%s)",
            updated_count, country, latest_session
        )
        return updated_count


# -------------------------------------------------------------------------
# ⏳ PLACEHOLDERS
# -------------------------------------------------------------------------

class MarketLowMetric:
    @staticmethod
    def update_from_quotes(country: str, enriched_rows):  # noqa: D401, F401
        pass


class MarketCloseMetric:
    @staticmethod
    def update_for_session(session_number: int):  # noqa: D401, F401
        pass


class MarketRangeMetric:
    @staticmethod
    def update_for_session(session_number: int):  # noqa: D401, F401
        pass
