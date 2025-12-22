"""MarketSession metrics system.

Defines metric update helpers for intraday calculations. Keep each metric
focused so they can be composed by background monitors without overlap.

Implemented:
    - MarketOpenMetric  → copies last_price → market_open after capture
        - MarketHighMetric  → updates market_high_open / market_high_pct_open

Placeholders (to implement later):
  - MarketLowMetric
  - MarketCloseMetric
  - MarketRangeMetric
"""

import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from ThorTrading.models.MarketSession import MarketSession

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


def _move_from_open_pct(open_price: Decimal | None, target_price: Decimal | None) -> Decimal | None:
    """Compute percent move from open to target, clamped at zero for non-positive moves."""
    if open_price in (None, 0) or target_price is None:
        return None
    try:
        move = target_price - open_price
        if move <= 0:
            return Decimal("0")
        return _quantize_pct((move / open_price) * Decimal("100"))
    except (InvalidOperation, ZeroDivisionError):
        return None


def _latest_capture_group(country: str):
    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )


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
            "id", "market_high_open", "market_low_open", "last_price", "market_high_pct_open", "market_low_pct_open"
        ):
            lp = session.last_price
            # Skip if we have no last price yet.
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
    Track intraday high and percent move from market open to that high
    for a country during the active market session.

    Logic:
    - market_high_open = highest last_price seen so far
    - market_high_pct_open = ((high - open) / open) * 100
        → 0% at the open
        → grows only when a new high is set
    """

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows) -> int:
        if not enriched_rows:
            return 0

        logger.info("MarketHighMetric → Updating %s", country)

        latest_group = _latest_capture_group(country)
        if latest_group is None:
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
                .filter(country=country, future=future, capture_group=latest_group)
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

            current_high = session.market_high_open
            open_price = session.market_open

            # FIRST TICK (no high recorded yet)
            if current_high is None:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                logger.debug("[DIAG High] FIRST TICK %s: set high=%s pct=%s", future, last_price, pct)
                updated_count += 1
                continue

            # NEW HIGH — reset percentage to 0
            if last_price > current_high:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                logger.debug(
                    "[DIAG High] NEW HIGH %s: last=%s prev_high=%s pct=%s",
                    future, last_price, current_high, pct
                )
                updated_count += 1
                continue

            # BELOW THE HIGH → no change to percent (still tracking peak move from open)
            logger.debug(
                "[DIAG High] BELOW HIGH %s: last=%s high=%s pct=%s",
                future,
                last_price,
                current_high,
                session.market_high_pct_open,
            )
            continue

        logger.info(
            "MarketHighMetric complete → %s updated (country=%s session=%s)",
            updated_count, country, latest_group
        )
        return updated_count


class MarketLowMetric:
    """Maintain intraday low price and percentage run-up from that low."""

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows) -> int:
        if not enriched_rows:
            return 0

        logger.info("MarketLowMetric → Updating %s", country)

        latest_group = _latest_capture_group(country)

        if latest_group is None:
            logger.info("MarketLowMetric → No sessions for %s", country)
            return 0

        updated_count = 0

        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")
            if not symbol:
                logger.debug("[DIAG Low] Skip row: missing symbol row=%s", row)
                continue

            future = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                logger.debug("[DIAG Low] Skip %s: last_price None raw_last=%s", future, row.get("last"))
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(
                    country=country,
                    future=future,
                    capture_group=latest_group,
                )
                .first()
            )
            if not session:
                logger.debug("[DIAG Low] No session row for %s country=%s session=%s", future, country, latest_session)
                continue

            current_low = session.market_low_open

            if current_low is None:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
                logger.debug("[DIAG Low] FIRST TICK %s: set low=%s pct=0", future, last_price)
                updated_count += 1
                continue

            if last_price < current_low:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
                logger.debug("[DIAG Low] NEW LOWER LOW %s: last=%s prev_low=%s pct=0", future, last_price, current_low)
                updated_count += 1
                continue

            try:
                move_up = last_price - current_low
                pct = (move_up / current_low) * Decimal("100") if current_low != 0 else None
            except (InvalidOperation, ZeroDivisionError):
                pct = None
            pct = _quantize_pct(pct)

            session.market_low_open = current_low
            session.market_low_pct_open = pct
            session.save(update_fields=["market_low_pct_open"])
            logger.debug("[DIAG Low] ABOVE LOW %s: last=%s low=%s runup=%s pct=%s", future, last_price, current_low, move_up if 'move_up' in locals() else None, pct)
            updated_count += 1

        logger.info(
            "MarketLowMetric complete → %s updated for %s (session %s)",
            updated_count, country, latest_group
        )
        return updated_count


class MarketCloseMetric:
    """
    Handles copying last_price → market_close and computing closing metrics
    when a market transitions from OPEN to CLOSED.

    This is a one-time event per session, unlike high/low which run continuously.

        Columns:
        - market_close                     = last_price at close
        - market_high_pct_close            = percent below the intraday high
        - market_low_pct_close             = percent above the intraday low
        - market_close_vs_open_pct  = (close - open) / open * 100
    """

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str, enriched_rows) -> int:
        """Store close metrics when a country's market transitions to CLOSED."""
        if not enriched_rows:
            return 0

        logger.info(
            "MarketCloseMetric → Closing values for %s at %s",
            country, timezone.now()
        )

        latest_group = _latest_capture_group(country)

        if latest_group is None:
            logger.info("MarketCloseMetric → No session for %s; skipping", country)
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
                .filter(
                    country=country,
                    future=future,
                    capture_group=latest_group,
                )
                .first()
            )
            if not session:
                continue

            session.market_close = last_price

            high_pct = None
            high_price = session.market_high_open
            if high_price not in (None, 0):
                try:
                    diff_high = high_price - last_price
                    if diff_high < 0:
                        diff_high = Decimal("0")
                    high_pct = (diff_high / high_price) * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    high_pct = None
            high_pct = _quantize_pct(high_pct)

            low_pct = None
            low_price = session.market_low_open
            if low_price not in (None, 0):
                try:
                    diff_low = last_price - low_price
                    if diff_low < 0:
                        diff_low = Decimal("0")
                    low_pct = (diff_low / low_price) * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    low_pct = None
            low_pct = _quantize_pct(low_pct)

            close_vs_open_pct = None
            open_price = session.market_open
            if open_price not in (None, 0):
                try:
                    move = last_price - open_price
                    close_vs_open_pct = (move / open_price) * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    close_vs_open_pct = None
            close_vs_open_pct = _quantize_pct(close_vs_open_pct)

            session.market_high_pct_close = high_pct
            session.market_low_pct_close = low_pct
            session.market_close_vs_open_pct = close_vs_open_pct
            session.save(update_fields=[
                "market_close",
                "market_high_pct_close",
                "market_low_pct_close",
                "market_close_vs_open_pct",
            ])
            updated_count += 1

        logger.info(
            "MarketCloseMetric complete → %s rows updated for %s (session %s)",
            updated_count, country, latest_group
        )
        return updated_count


class MarketRangeMetric:
    """
    Computes full intraday range for each (country, future) at market close.

    Columns:
    - market_range            = market_high_open - market_low_open
    - market_range_pct        = (market_range / market_open) * 100

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
        latest_group = _latest_capture_group(country)
        if latest_group is None:
            logger.info("MarketRangeMetric → No session for %s; skipping", country)
            return 0

        sessions = (
            MarketSession.objects
            .select_for_update()
            .filter(country=country, capture_group=latest_group)
        )

        updated_count = 0

        for session in sessions:
            high = session.market_high_open
            low = session.market_low_open
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

            session.market_range = range_number
            session.market_range_pct = pct
            session.save(
                update_fields=[
                    "market_range",
                    "market_range_pct",
                ]
            )
            updated_count += 1

        logger.info(
            "MarketRangeMetric complete → %s rows updated for %s (capture_group=%s)",
            updated_count, country, latest_group
        )
        return updated_count

