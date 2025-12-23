"""Market open capture supervisor utilities.

Provides the looping helper used by the Thor background stack to
continuously monitor control markets and trigger the MarketOpenCapture
service exactly once per market per session.
"""

from __future__ import annotations

import logging
import os
from datetime import date as date_cls

from django.conf import settings
from django.utils import timezone

from ThorTrading.services.country_codes import normalize_country_code
from ThorTrading.views.MarketOpenCapture import capture_market_open as _view_capture_market_open

logger = logging.getLogger(__name__)


def _get_capture_interval() -> float:
    setting = getattr(settings, "FUTURETRADING_MARKET_OPEN_CAPTURE_INTERVAL", None)
    if setting is not None:
        try:
            return max(1.0, float(setting))
        except (TypeError, ValueError):
            logger.warning("Invalid FUTURETRADING_MARKET_OPEN_CAPTURE_INTERVAL setting %r", setting)
    env = os.getenv("FUTURETRADING_MARKET_OPEN_CAPTURE_INTERVAL")
    if env:
        try:
            return max(1.0, float(env))
        except (TypeError, ValueError):
            logger.warning("Invalid FUTURETRADING_MARKET_OPEN_CAPTURE_INTERVAL env %r", env)
    return 1.0


def _market_local_date(market) -> date_cls:
    info = None
    try:
        info = market.get_current_market_time()
    except Exception:
        info = None
    if info:
        return date_cls(info["year"], info["month"], info["date"])
    return timezone.now().date()


def _has_capture_for_date(market, capture_date: date_cls) -> bool:
    from ThorTrading.models.MarketSession import MarketSession

    country_code = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
    latest = (
        MarketSession.objects.filter(country=country_code)
        .exclude(capture_group__isnull=True)
        .order_by("-capture_group")
        .first()
    )
    if not latest:
        return False
    return (
        latest.year == capture_date.year
        and latest.month == capture_date.month
        and latest.date == capture_date.day
    )


def _scan_and_capture_once():
    from GlobalMarkets.models.market import Market

    markets = Market.objects.filter(is_active=True, is_control_market=True)

    for market in markets:
        if not getattr(market, "enable_futures_capture", True):
            continue
        if not getattr(market, "enable_open_capture", True):
            continue
        if market.status != "OPEN":
            continue

        market_date = _market_local_date(market)
        try:
            already_captured = _has_capture_for_date(market, market_date)
        except Exception:
            logger.exception("Failed checking capture history for %s", market.country)
            continue

        if already_captured:
            continue

        logger.info("🌅 Market %s opened with no capture for %s — running capture", market.country, market_date)
        try:
            capture_market_open(market)
        except Exception:
            logger.exception("Market open capture failed for %s", market.country)
        else:
            logger.info("✅ Market open capture complete for %s", market.country)


def check_for_market_opens_and_capture() -> float:
    """Execute one capture scan and return the sleep interval."""

    interval = _get_capture_interval()
    if not getattr(check_for_market_opens_and_capture, "_logged_start", False):
        logger.info("🌎 Market Open Capture loop ready (interval=%.1fs)", interval)
        check_for_market_opens_and_capture._logged_start = True

    _scan_and_capture_once()
    return interval


def capture_market_open(market):
    """Proxy to the view-layer MarketOpenCapture service for backward compatibility."""

    return _view_capture_market_open(market)


__all__ = [
    "capture_market_open",
    "check_for_market_opens_and_capture",
]

