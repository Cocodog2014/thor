# ThorTrading/services/metrics/session_close_range.py

import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


def _quantize_pct(pct: Decimal | None) -> Decimal | None:
    if pct is None:
        return None
    try:
        return pct.quantize(Decimal("0.0001"))
    except Exception:
        return pct


def _safe_decimal(val):
    from decimal import Decimal as D
    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


class MarketCloseMetric:
    """Copy last_price → market_close and compute close metrics."""

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str, enriched_rows) -> int:
        if not enriched_rows:
            return 0

        logger.info(
            "MarketCloseMetric → Closing values for %s at %s",
            country, timezone.now(),
        )

        latest_group = (
            MarketSession.objects
            .filter(country=country)
            .exclude(capture_group__isnull=True)
            .order_by('-capture_group')
            .values_list('capture_group', flat=True)
            .first()
        )
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
                .filter(country=country, future=future, capture_group=latest_group)
                .first()
            )
            if not session:
                continue

            session.market_close = last_price

            # % below intraday high
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

            # % above intraday low
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

            # close vs open %
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
            "MarketCloseMetric complete → %s rows updated for %s (capture_group %s)",
            updated_count, country, latest_group,
        )
        return updated_count


class MarketRangeMetric:
    """Compute full intraday range at market close."""

    @staticmethod
    @transaction.atomic
    def update_for_country_on_close(country: str) -> int:
        logger.info(
            "MarketRangeMetric → Computing range for %s at %s",
            country, timezone.now(),
        )

        latest_group = (
            MarketSession.objects
            .filter(country=country)
            .exclude(capture_group__isnull=True)
            .order_by('-capture_group')
            .values_list('capture_group', flat=True)
            .first()
        )
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
            "MarketRangeMetric complete → %s rows updated for %s (capture_group=%s)",
            updated_count, country, latest_group,
        )
        return updated_count

