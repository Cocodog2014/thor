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


def _quantize_pct(pct: Decimal | None) -> Decimal | None:
    """Force percentage values to four decimal places if not None."""
    if pct is None:
        return None
    try:
        return pct.quantize(Decimal('0.0001'))
    except Exception:
        return pct


# -------------------------------------------------------------------------
# ⭐ MARKET OPEN METRIC
# -------------------------------------------------------------------------

class MarketOpenMetric:
    """Populate market_open = last_price for all rows in a session."""

    @staticmethod
    def update(session_number: int) -> int:
        logger.info("MarketOpenMetric → Session %s", session_number)

        # First set market_open from last_price for all rows in this session.
        base_qs = MarketSession.objects.filter(session_number=session_number)
        open_updated = base_qs.update(market_open=F("last_price"))

        # Initialize high/low columns at the moment of open so the dashboard
        # immediately shows starting values instead of nulls. We only set them
        # if not already populated (defensive against re-runs).
        initialized_count = 0
        for session in base_qs.only(
            "id", "market_high_number", "market_low_number", "last_price", "market_high_percentage", "market_low_percentage"
        ):
            lp = session.last_price
            # Skip if we have no last price yet.
            if lp in (None, 0):
                continue
            to_update = []
            if session.market_high_number is None:
                session.market_high_number = lp
                session.market_high_percentage = Decimal("0")
                to_update.extend(["market_high_number", "market_high_percentage"])
            if session.market_low_number is None:
                session.market_low_number = lp
                session.market_low_percentage = Decimal("0")
                to_update.extend(["market_low_number", "market_low_percentage"])
            if to_update:
                session.save(update_fields=to_update)
                initialized_count += 1

        total = open_updated  # rows where open price copied
        logger.info(
            "MarketOpenMetric complete → %s open prices, %s high/low initialized (session %s)",
            open_updated, initialized_count, session_number
        )
        return total


# -------------------------------------------------------------------------
# ⭐ MARKET HIGH METRIC
# -------------------------------------------------------------------------

class MarketHighMetric:
    """
    Track intraday high AND percentage drawdown from that high
    for a country during the active market session.

    Logic:
      - market_high_number = highest last_price seen so far
      - market_high_percentage = ((high - last_price) / high) * 100
            → 0% at the high
            → grows as price falls below the high
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
                logger.debug("[DIAG High] Skip row: missing symbol row=%s", row)
                continue

            future = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                logger.debug("[DIAG High] Skip %s: last_price None raw_last=%s", future, row.get("last"))
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(country=country, future=future, session_number=latest_session)
                .first()
            )
            if not session:
                logger.debug("[DIAG High] No session row for %s country=%s session=%s", future, country, latest_session)
                continue

            # You must have a valid open to compute anything
            market_open = session.market_open
            if market_open is None or market_open == 0:
                logger.debug("[DIAG High] Skip %s: market_open missing (%s)", future, market_open)
                continue

            current_high = session.market_high_number

            # FIRST TICK (no high recorded yet)
            if current_high is None:
                session.market_high_number = last_price
                session.market_high_percentage = Decimal("0")  # at the high
                session.save(update_fields=["market_high_number", "market_high_percentage"])
                logger.debug("[DIAG High] FIRST TICK %s: set high=%s pct=0", future, last_price)
                updated_count += 1
                continue

            # NEW HIGH — reset percentage to 0
            if last_price > current_high:
                session.market_high_number = last_price
                session.market_high_percentage = Decimal("0")
                session.save(update_fields=["market_high_number", "market_high_percentage"])
                logger.debug("[DIAG High] NEW HIGH %s: last=%s prev_high=%s pct=0", future, last_price, current_high)
                updated_count += 1
                continue

            # BELOW THE HIGH → compute drawdown-from-high
            try:
                drawdown = current_high - last_price
                pct = (drawdown / current_high) * Decimal("100")
            except (InvalidOperation, ZeroDivisionError):
                pct = None
            pct = _quantize_pct(pct)

            session.market_high_number = current_high  # unchanged
            session.market_high_percentage = pct
            session.save(update_fields=["market_high_percentage"])
            logger.debug("[DIAG High] BELOW HIGH %s: last=%s high=%s drawdown=%s pct=%s", future, last_price, current_high, drawdown if 'drawdown' in locals() else None, pct)
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
    """
    Tracks intraday low and percentage run-up from that low for each
    (country, future) while the market is open.

    Columns:
      - market_low_number      = lowest last_price seen so far
      - market_low_percentage  = (last_price - low) / low * 100
            → 0% at the low
            → grows as price moves ABOVE the low
    """

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows) -> int:
        """
        Update market_low_number and market_low_percentage for the latest
        session for `country` using a batch of enriched quote rows.

        `enriched_rows` should be the same structure returned by
        get_enriched_quotes_with_composite().
        """
        if not enriched_rows:
            return 0

        logger.info(
            "MarketLowMetric → Updating lows for %s at %s",
            country, timezone.now()
        )

        # Latest session for this country (current open session)
        latest_session = (
            MarketSession.objects
            .filter(country=country)
            .aggregate(max_session=Max("session_number"))
            .get("max_session")
        )

        if latest_session is None:
            logger.info("MarketLowMetric → No sessions yet for %s; skipping", country)
            return 0

        updated_count = 0

        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")  # e.g. "/YM"
            if not symbol:
                logger.debug("[DIAG Low] Skip row: missing symbol row=%s", row)
                continue
            future = symbol.lstrip("/").upper()               # normalize to "YM"

            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                logger.debug("[DIAG Low] Skip %s: last_price None raw_last=%s", future, row.get("last"))
                continue

            # Lock the current session row for this future
            session = (
                MarketSession.objects
                .select_for_update()
                .filter(
                    country=country,
                    future=future,
                    session_number=latest_session,
                )
                .first()
            )
            if not session:
                logger.debug("[DIAG Low] No session row for %s country=%s session=%s", future, country, latest_session)
                continue

            current_low = session.market_low_number

            # FIRST TICK (no low recorded yet)
            if current_low is None:
                session.market_low_number = last_price
                session.market_low_percentage = Decimal("0")  # at the low
                session.save(update_fields=["market_low_number", "market_low_percentage"])
                logger.debug("[DIAG Low] FIRST TICK %s: set low=%s pct=0", future, last_price)
                updated_count += 1
                continue

            # NEW LOWER LOW → reset run-up to 0
            if last_price < current_low:
                session.market_low_number = last_price
                session.market_low_percentage = Decimal("0")
                session.save(update_fields=["market_low_number", "market_low_percentage"])
                logger.debug("[DIAG Low] NEW LOWER LOW %s: last=%s prev_low=%s pct=0", future, last_price, current_low)
                updated_count += 1
                continue

            # ABOVE THE LOW → compute run-up from low: (last - low) / low * 100
            try:
                move_up = last_price - current_low
                pct = (move_up / current_low) * Decimal("100") if current_low != 0 else None
            except (InvalidOperation, ZeroDivisionError):
                pct = None
            pct = _quantize_pct(pct)

            session.market_low_number = current_low  # unchanged
            session.market_low_percentage = pct
            session.save(update_fields=["market_low_percentage"])
            logger.debug("[DIAG Low] ABOVE LOW %s: last=%s low=%s runup=%s pct=%s", future, last_price, current_low, move_up if 'move_up' in locals() else None, pct)
            updated_count += 1

        logger.info(
            "MarketLowMetric complete → %s rows updated for %s (session %s)",
            updated_count, country, latest_session
        )
        return updated_count


class MarketCloseMetric:
    """
    Handles copying last_price → market_close_number and computing
    market_close_percentage when a market transitions from OPEN to CLOSED.

    This is a one-time event per session, unlike high/low which run continuously.

    Columns:
      - market_close_number     = last_price at close
      - market_close_percentage = (close - open) / open * 100
    """

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str, enriched_rows) -> int:
        """
        Called when a country’s market status flips to CLOSED.

        - Determine the latest session_number for that country
        - Copy last_price (from live enriched feed) into market_close_number
        - Compute market_close_percentage vs market_open
        """
        if not enriched_rows:
            return 0

        logger.info(
            "MarketCloseMetric → Closing values for %s at %s",
            country, timezone.now()
        )

        # Find latest session for this country
        latest_session = (
            MarketSession.objects
            .filter(country=country)
            .aggregate(max_session=Max("session_number"))
            .get("max_session")
        )

        if latest_session is None:
            logger.info("MarketCloseMetric → No session for %s; skipping", country)
            return 0

        updated_count = 0

        # Update each future’s close price + percentage move from open
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
                .filter(
                    country=country,
                    future=future,
                    session_number=latest_session,
                )
                .first()
            )
            if not session:
                continue

            session.market_close_number = last_price

            # Percentage move from open: (close - open) / open * 100
            pct = None
            open_price = session.market_open
            if open_price not in (None, 0):
                try:
                    move = last_price - open_price
                    pct = (move / open_price) * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    pct = None

            session.market_close_percentage = pct
            session.save(update_fields=["market_close_number", "market_close_percentage"])
            updated_count += 1

        logger.info(
            "MarketCloseMetric complete → %s rows updated for %s (session %s)",
            updated_count, country, latest_session
        )
        return updated_count


class MarketRangeMetric:
    """
    Computes full intraday range for each (country, future) at market close.

    Columns:
      - market_range_number     = market_high_number - market_low_number
      - market_range_percentage = (market_range_number / market_open) * 100

    This should be called once when a market transitions to CLOSED,
    after high/low metrics have already been updated for the session.
    """

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str) -> int:
        logger.info(
            "MarketRangeMetric → Computing range for %s at %s",
            country, timezone.now()
        )

        # Latest session for this country
        latest_session = (
            MarketSession.objects
            .filter(country=country)
            .aggregate(max_session=Max("session_number"))
            .get("max_session")
        )
        if latest_session is None:
            logger.info("MarketRangeMetric → No session for %s; skipping", country)
            return 0

        sessions = (
            MarketSession.objects
            .select_for_update()
            .filter(country=country, session_number=latest_session)
        )

        updated_count = 0

        for session in sessions:
            high = session.market_high_number
            low = session.market_low_number
            open_price = session.market_open

            # Need both a high and a low to compute range
            if high is None or low is None:
                continue

            range_number = high - low

            pct = None
            if open_price not in (None, 0):
                try:
                    pct = (range_number / open_price) * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    pct = None

            session.market_range_number = range_number
            session.market_range_percentage = pct
            session.save(
                update_fields=[
                    "market_range_number",
                    "market_range_percentage",
                ]
            )
            updated_count += 1

        logger.info(
            "MarketRangeMetric complete → %s rows updated for %s (session=%s)",
            updated_count, country, latest_session
        )
        return updated_count
