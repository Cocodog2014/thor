from __future__ import annotations
"""MarketSession metrics (open/high/low/close/range)."""

import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from ThorTrading.studies.futures_total.models.market_session import MarketSession
from GlobalMarkets.services import normalize_country_code

logger = logging.getLogger(__name__)


def _safe_decimal(val):
    if val in (None, "", " "):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _normalize_country(country: str) -> str:
    normalized = normalize_country_code(country)
    return normalized or country


def _quantize_pct(pct: Decimal | None) -> Decimal | None:
    if pct is None:
        return None
    try:
        return pct.quantize(Decimal("0.0001"))
    except Exception:
        return pct


def _move_from_open_pct(open_price: Decimal | None, target_price: Decimal | None) -> Decimal | None:
    if open_price in (None, 0) or target_price is None:
        return None
    try:
        move = target_price - open_price
        if move <= 0:
            return Decimal("0")
        return _quantize_pct((move / open_price) * Decimal("100"))
    except (InvalidOperation, ZeroDivisionError):
        return None


def _resolve_session_number(country: str, session_number: int | None = None) -> int | None:
    """
    Resolve the session_number to update.

    If a session_number is provided, use it.
    Otherwise choose the latest session_number for that country.
    """
    if session_number is not None:
        return session_number

    country = _normalize_country(country)
    return (
        MarketSession.objects
        .filter(country=country)
        .order_by("-session_number")
        .values_list("session_number", flat=True)
        .first()
    )


class MarketOpenMetric:
    """Populate market_open = last_price for all rows in a session."""

    @staticmethod
    def update(session_number: int) -> int:
        return MarketOpenMetric.update_for_session_number(session_number)

    @staticmethod
    def update_for_session_number(session_number: int) -> int:
        logger.info("MarketOpenMetric → session_number %s", session_number)

        base_qs = MarketSession.objects.filter(session_number=session_number)
        open_updated = base_qs.update(market_open=F("last_price"))

        initialized_count = 0
        for session in base_qs.only(
            "id", "market_high_open", "market_low_open", "last_price", "market_high_pct_open", "market_low_pct_open"
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
            "MarketOpenMetric complete → %s open prices, %s high/low initialized (session_number %s)",
            open_updated, initialized_count, session_number
        )
        return open_updated

    @staticmethod
    def update_latest_for_country(country: str, *, session_number: int | None = None) -> int:
        country = _normalize_country(country)
        session_number = _resolve_session_number(country, session_number)
        if session_number is None:
            logger.info("MarketOpenMetric → No session_number found for %s", country)
            return 0
        return MarketOpenMetric.update_for_session_number(session_number)


class MarketHighMetric:
    """Track intraday high and percent move from market open to that high."""

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows, *, session_number: int | None = None) -> int:
        if not enriched_rows:
            return 0

        country = _normalize_country(country)

        logger.info("MarketHighMetric → Updating %s", country)

        session_number = _resolve_session_number(country, session_number)
        if session_number is None:
            logger.info("MarketHighMetric → No sessions for %s", country)
            return 0

        updated_count = 0

        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")
            if not symbol:
                logger.debug("[DIAG High] Skip row: missing symbol row=%s", row)
                continue

            base_symbol = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                logger.debug("[DIAG High] Skip %s: last_price None raw_last=%s", base_symbol, row.get("last"))
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(country=country, symbol=base_symbol, session_number=session_number)
                .first()
            )
            if not session:
                logger.debug("[DIAG High] No session row for %s country=%s session_number=%s", base_symbol, country, session_number)
                continue

            market_open = session.market_open
            if market_open is None or market_open == 0:
                logger.debug("[DIAG High] Skip %s: market_open missing (%s)", base_symbol, market_open)
                continue

            current_high = session.market_high_open
            open_price = session.market_open

            if current_high is None:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                logger.debug("[DIAG High] FIRST TICK %s: set high=%s pct=%s", base_symbol, last_price, pct)
                updated_count += 1
                continue

            if last_price > current_high:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                logger.debug(
                    "[DIAG High] NEW HIGH %s: last=%s prev_high=%s pct=%s",
                    base_symbol, last_price, current_high, pct
                )
                updated_count += 1
                continue

            logger.debug(
                "[DIAG High] BELOW HIGH %s: last=%s high=%s pct=%s",
                base_symbol,
                last_price,
                current_high,
                session.market_high_pct_open,
            )

        logger.info(
            "MarketHighMetric complete → %s updated (country=%s session_number=%s)",
            updated_count, country, session_number
        )
        return updated_count


class MarketLowMetric:
    """Maintain intraday low price and percentage run-up from that low."""

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows, *, session_number: int | None = None) -> int:
        if not enriched_rows:
            return 0

        country = _normalize_country(country)

        logger.info("MarketLowMetric → Updating %s", country)

        session_number = _resolve_session_number(country, session_number)
        if session_number is None:
            logger.info("MarketLowMetric → No sessions for %s", country)
            return 0

        updated_count = 0

        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")
            if not symbol:
                logger.debug("[DIAG Low] Skip row: missing symbol row=%s", row)
                continue

            base_symbol = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                logger.debug("[DIAG Low] Skip %s: last_price None raw_last=%s", base_symbol, row.get("last"))
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(
                    country=country,
                    symbol=base_symbol,
                    session_number=session_number,
                )
                .first()
            )
            if not session:
                logger.debug("[DIAG Low] No session row for %s country=%s session_number=%s", base_symbol, country, session_number)
                continue

            current_low = session.market_low_open

            if current_low is None:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
                logger.debug("[DIAG Low] FIRST TICK %s: set low=%s pct=0", base_symbol, last_price)
                updated_count += 1
                continue

            if last_price < current_low:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
                logger.debug("[DIAG Low] NEW LOWER LOW %s: last=%s prev_low=%s pct=0", base_symbol, last_price, current_low)
                updated_count += 1
                continue

            try:
                move_up = last_price - current_low
                pct = (move_up / current_low) * Decimal("100") if current_low != 0 else None
            except (InvalidOperation, ZeroDivisionError):
                pct = None
            pct = _quantize_pct(pct)

            if pct != session.market_low_pct_open:
                session.market_low_pct_open = pct
                session.save(update_fields=["market_low_pct_open"])
                updated_count += 1
                logger.debug(
                    "[DIAG Low] ABOVE LOW %s: last=%s low=%s runup=%s pct=%s",
                    base_symbol,
                    last_price,
                    current_low,
                    move_up if "move_up" in locals() else None,
                    pct,
                )

        logger.info(
            "MarketLowMetric complete → %s updated for %s (session_number %s)",
            updated_count, country, session_number
        )
        return updated_count


class MarketCloseMetric:
    """Copy last_price → market_close and compute close metrics."""

    @staticmethod
    def _neutralize_unhit_sessions(country: str, session_number: int) -> int:
        """Set wndw=NEUTRAL when no target/stop was hit during the session."""
        country = _normalize_country(country)
        pending = (
            MarketSession.objects
            .filter(country=country, session_number=session_number, wndw="PENDING")
        )

        updated = 0
        for session in pending:
            signal = (session.bhs or "").upper()
            th = session.target_high
            tl = session.target_low
            high = session.market_high_open
            low = session.market_low_open

            hit_target = False
            hit_stop = False

            if signal in ["BUY", "STRONG_BUY"]:
                hit_target = bool(high is not None and th is not None and high >= th)
                hit_stop = bool(low is not None and tl is not None and low <= tl)
            elif signal in ["SELL", "STRONG_SELL"]:
                hit_target = bool(low is not None and tl is not None and low <= tl)
                hit_stop = bool(high is not None and th is not None and high >= th)

            if hit_target or hit_stop:
                continue

            session.wndw = "NEUTRAL"
            session.save(update_fields=["wndw"])
            updated += 1

        if updated:
            logger.info(
                "MarketCloseMetric → Neutralized %s pending sessions for %s (session_number %s)",
                updated,
                country,
                session_number,
            )
        return updated

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str, enriched_rows, *, session_number: int | None = None) -> int:
        if not enriched_rows:
            return 0

        country = _normalize_country(country)

        logger.info(
            "MarketCloseMetric → Closing values for %s at %s",
            country, timezone.now(),
        )

        session_number = _resolve_session_number(country, session_number)
        if session_number is None:
            logger.info("MarketCloseMetric → No session for %s; skipping", country)
            return 0

        updated_count = 0

        for row in enriched_rows:
            symbol = row.get("instrument", {}).get("symbol")
            if not symbol:
                continue

            base_symbol = symbol.lstrip("/").upper()
            last_price = _safe_decimal(row.get("last"))
            if last_price is None:
                continue

            session = (
                MarketSession.objects
                .select_for_update()
                .filter(country=country, symbol=base_symbol, session_number=session_number)
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
            "MarketCloseMetric complete → %s rows updated for %s (session_number %s)",
            updated_count, country, session_number,
        )

        try:
            MarketCloseMetric._neutralize_unhit_sessions(country, session_number)
        except Exception:
            logger.exception(
                "MarketCloseMetric → pending neutralization failed for %s (session_number %s)",
                country,
                session_number,
            )
        return updated_count


class MarketRangeMetric:
    """Compute full intraday range at market close."""

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str, *, session_number: int | None = None) -> int:
        country = _normalize_country(country)
        logger.info(
            "MarketRangeMetric → Computing range for %s at %s",
            country, timezone.now(),
        )

        session_number = _resolve_session_number(country, session_number)
        if session_number is None:
            logger.info("MarketRangeMetric → No session for %s; skipping", country)
            return 0

        sessions = (
            MarketSession.objects
            .select_for_update()
            .filter(country=country, session_number=session_number)
        )

        updated_count = 0
        for session in sessions:
            high = session.market_high_open
            low = session.market_low_open
            open_price = session.market_open

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
            session.save(update_fields=["market_range", "market_range_pct"])
            updated_count += 1

        logger.info(
            "MarketRangeMetric complete → %s rows updated for %s (session_number=%s)",
            updated_count, country, session_number,
        )
        return updated_count


__all__ = [
    "MarketOpenMetric",
    "MarketHighMetric",
    "MarketLowMetric",
    "MarketCloseMetric",
    "MarketRangeMetric",
]
