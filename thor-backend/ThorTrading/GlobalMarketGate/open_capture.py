from __future__ import annotations

import logging
import os
from ThorTrading.studies.futures_total.services.session_capture import (  # noqa: F401
    MarketOpenCaptureService,
    _market_local_date,
    capture_market_open,
    check_for_market_opens_and_capture,
)

__all__ = [
    "capture_market_open",
    "check_for_market_opens_and_capture",
    "MarketOpenCaptureService",
    "_market_local_date",
]

    env = os.getenv("THORTRADING_MARKET_OPEN_CAPTURE_INTERVAL") or os.getenv("TRADING_MARKET_OPEN_CAPTURE_INTERVAL")
    if env:
        try:
            return max(1.0, float(env))
        except (TypeError, ValueError):
            logger.warning("Invalid market open capture interval env %r", env)

    return 1.0


def _market_timezone(market) -> ZoneInfo:
    tz_name = getattr(market, "timezone_name", None) or getattr(market, "timezone", None)
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning(
                "Unknown timezone %s for %s; using default timezone instead",
                tz_name,
                getattr(market, "country", "?"),
            )

    try:
        default_tz = timezone.get_default_timezone()
        key = getattr(default_tz, "key", None) or getattr(default_tz, "zone", None) or str(default_tz)
        return ZoneInfo(key)
    except Exception:
        return timezone.utc


def _market_time_info(market) -> dict:
    market_now = timezone.now().astimezone(_market_timezone(market))
    return {
        "year": market_now.year,
        "month": market_now.month,
        "date": market_now.day,
        "day": market_now.strftime("%a"),
        "date_obj": market_now.date(),
    }


def _market_local_date(market) -> date_cls:
    try:
        return _market_time_info(market)["date_obj"]
    except Exception:
        return timezone.now().date()


def _scan_and_capture_once() -> int:
    """
    Scan all control markets and capture OPEN for any market that is OPEN now
    and not yet captured for the current session_number.
    """
    captures = 0

    markets = list(get_control_markets())
    if not markets:
        return 0

    session_number = None
    try:
        session_number = live_data_redis.get_active_session_number()
    except Exception:
        session_number = None

    if session_number is None:
        return 0

    session_number = int(session_number)
    if MarketSession.objects.filter(session_number=session_number, capture_kind="OPEN").exists():
        return 0

    for market in markets:
        country_code = getattr(market, "country", None)
        if not country_code:
            continue

        try:
            if not is_market_open_now(market):
                continue
        except Exception:
            logger.exception("OpenCapture scan: failed open check for %s", country_code)
            continue

        try:
            result = capture_market_open(market, session_number=session_number)
            if result is not None:
                logger.info("OpenCapture scan: captured %s => %s", country_code, result)
                captures += 1
        except Exception:
            logger.exception("OpenCapture scan: capture failed for %s", country_code)

    return captures


def check_for_market_opens_and_capture() -> float:
    """Execute one capture scan and return the sleep interval."""
    interval = _get_capture_interval()
    if not getattr(check_for_market_opens_and_capture, "_logged_start", False):
        logger.info("🌎 Market Open Capture loop ready (interval=%.1fs)", interval)
        check_for_market_opens_and_capture._logged_start = True

    _scan_and_capture_once()
    return interval


def capture_market_open(market, *, session_number: int | None = None):
    """Main entry point for market open capture."""
    return _service.capture_market_open(market, session_number=session_number)


__all__ = [
    "capture_market_open",
    "check_for_market_opens_and_capture",
    "MarketOpenCaptureService",
]
