# ThorTrading/services/metrics/session_high_low.py

import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


def _safe_decimal(val):
    from decimal import Decimal as D
    if val in (None, "", " "):
        return None
    try:
        return D(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


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


class MarketHighMetric:
    """Track intraday high and percent move from open to that high."""

    @staticmethod
    @transaction.atomic
    def update_from_quotes(country: str, enriched_rows) -> int:
        if not enriched_rows:
            return 0

        logger.info("MarketHighMetric → Updating %s", country)

        latest_group = (
            MarketSession.objects
            .filter(country=country)
            .exclude(capture_group__isnull=True)
            .order_by('-capture_group')
            .values_list('capture_group', flat=True)
            .first()
        )
        if latest_group is None:
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
                .filter(country=country, future=future, capture_group=latest_group)
                .first()
            )
            if not session:
                continue

            market_open = session.market_open
            if market_open is None or market_open == 0:
                continue

            current_high = session.market_high_open
            open_price = session.market_open

            if current_high is None:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                updated_count += 1
                continue

            if last_price > current_high:
                session.market_high_open = last_price
                pct = _move_from_open_pct(open_price, last_price) or Decimal("0")
                session.market_high_pct_open = pct
                session.save(update_fields=["market_high_open", "market_high_pct_open"])
                updated_count += 1
                continue

        logger.info(
            "MarketHighMetric complete → %s updated (country=%s capture_group=%s)",
            updated_count, country, latest_group,
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

        latest_group = (
            MarketSession.objects
            .filter(country=country)
            .exclude(capture_group__isnull=True)
            .order_by('-capture_group')
            .values_list('capture_group', flat=True)
            .first()
        )
        if latest_group is None:
            logger.info("MarketLowMetric → No sessions for %s", country)
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

            current_low = session.market_low_open

            if current_low is None:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
                updated_count += 1
                continue

            if last_price < current_low:
                session.market_low_open = last_price
                session.market_low_pct_open = Decimal("0")
                session.save(update_fields=["market_low_open", "market_low_pct_open"])
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
            updated_count += 1

        logger.info(
            "MarketLowMetric complete → %s updated for %s (capture_group %s)",
            updated_count, country, latest_group,
        )
        return updated_count

