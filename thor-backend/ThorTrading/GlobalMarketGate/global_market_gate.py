"""
ThorTrading Global Market Gate (ONE DOOR)

This module is the single integration point between:
- GlobalMarkets app (market_opened / market_closed signals)
and
- ThorTrading session/intraday capture services

Design goals:
- One file to understand the integration.
- No shims / no duplicate hook modules.
- Clear gating (feature flags live on Market model: enable_* fields).
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Set

from django.dispatch import receiver

from GlobalMarkets.models.market import Market
from GlobalMarkets.signals import market_closed, market_opened

from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.config.markets import CONTROL_COUNTRIES

# Capture implementations live in THIS folder (import lazily inside functions)

# Optional grading service (only if NOT using heartbeat mode)
from ThorTrading.services.sessions.grading import start_grading_service, stop_grading_service

logger = logging.getLogger(__name__)

# Master switch: allow GlobalMarkets -> ThorTrading orchestration at all
GLOBAL_TIMER_ENABLED = os.environ.get("THOR_USE_GLOBAL_MARKET_TIMER", "1").lower() not in {
    "0", "false", "no",
}

CONTROLLED_COUNTRIES = set(CONTROL_COUNTRIES)

_ACTIVE_COUNTRIES: Set[str] = set()
_ACTIVE_LOCK = threading.RLock()


# -----------------------------------------------------------------------------
# Scheduler mode
# -----------------------------------------------------------------------------
def _heartbeat_mode_active() -> bool:
    """
    When heartbeat scheduler is active, we should NOT manually start/stop
    grading services here (heartbeat owns job scheduling).
    """
    return os.environ.get("THOR_SCHEDULER_MODE", "heartbeat").lower() == "heartbeat"


# -----------------------------------------------------------------------------
# Gate helpers (ONE source of truth)
# -----------------------------------------------------------------------------
def market_enabled(market: Market) -> bool:
    return bool(getattr(market, "is_active", False))


def session_tracking_allowed(market_or_country: Market | str | None) -> bool:
    """
    Pure helper: look up the current session-capture flag for a country.

    Accepts either a Market instance or a country code/string to avoid
    relying on potentially stale in-memory flags. Queries are limited to
    the enable_session_capture + is_active columns to keep the lookup light.
    """
    if market_or_country is None:
        return False

    # Accept both Market instances and plain country strings for flexibility
    country = (
        market_or_country if isinstance(market_or_country, str)
        else getattr(market_or_country, "country", None)
    )

    country_code = normalize_country_code(country) or country
    if not country_code:
        return False

    try:
        market = (
            Market.objects
            .filter(country=country_code)
            .only("enable_session_capture", "is_active")
            .first()
        )
    except Exception:
        logger.exception("GlobalMarketGate: session_tracking_allowed lookup failed for %s", country_code)
        return False

    return bool(market and getattr(market, "is_active", False) and getattr(market, "enable_session_capture", False))


def open_capture_allowed(market: Market) -> bool:
    """
    Controls whether ThorTrading should capture market OPEN events for this market.
    """
    return market_enabled(market) and bool(getattr(market, "enable_open_capture", True))


def close_capture_allowed(market: Market) -> bool:
    """
    Controls whether ThorTrading should capture market CLOSE events for this market.
    """
    return market_enabled(market) and bool(getattr(market, "enable_close_capture", True))


def _is_controlled_market(market: Market | None) -> bool:
    """
    Controlled markets are the ones we care about for the global session pipeline.
    This is based on CONTROL_COUNTRIES (ThorTrading/config/markets.py).
    """
    if market is None or not market_enabled(market):
        return False

    normalized = normalize_country_code(getattr(market, "country", None))
    if normalized and normalized in CONTROLLED_COUNTRIES:
        return True

    country = getattr(market, "country", None)
    return country in CONTROLLED_COUNTRIES if country else False


def _skip(reason: str):
    logger.debug("GlobalMarketGate skipped: %s", reason)


# -----------------------------------------------------------------------------
# Active market tracking (used only for “first open” / “last close” behavior)
# -----------------------------------------------------------------------------
def _register_open(country: str) -> bool:
    """
    Returns True if this open makes the active-set go from empty->non-empty.
    """
    with _ACTIVE_LOCK:
        was_empty = not _ACTIVE_COUNTRIES
        _ACTIVE_COUNTRIES.add(country)
        return was_empty


def _register_close(country: str) -> bool:
    """
    Returns True if this close makes the active-set go from non-empty->empty.
    """
    with _ACTIVE_LOCK:
        was_member = country in _ACTIVE_COUNTRIES
        if was_member:
            _ACTIVE_COUNTRIES.remove(country)
        return was_member and not _ACTIVE_COUNTRIES


def _start_global_background_services():
    """
    If you ever need “global once-per-any-market-open” services, do them here.
    Currently heartbeat jobs own most background work.
    """
    logger.debug("GlobalMarketGate: no legacy global background services to start.")


def _stop_global_background_services():
    """
    Stop anything started in _start_global_background_services.
    """
    logger.debug("GlobalMarketGate: no legacy global background services to stop.")


# -----------------------------------------------------------------------------
# Bootstrap (process startup)
# -----------------------------------------------------------------------------
def bootstrap_open_markets():
    """
    On server start, GlobalMarkets may already have markets in OPEN status.
    Bootstrap workers so ThorTrading is consistent after restart.
    """
    if not GLOBAL_TIMER_ENABLED:
        return

    try:
        open_markets = Market.objects.filter(is_active=True, status="OPEN")
    except Exception:
        logger.exception("GlobalMarketGate: failed to query open markets")
        return

    controlled = [m for m in open_markets if _is_controlled_market(m)]
    if not controlled:
        return

    logger.info("GlobalMarketGate: bootstrapping %s open market(s)", len(controlled))

    for market in controlled:
        country = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
        _register_open(country)

    _start_global_background_services()

    if _heartbeat_mode_active():
        logger.info("GlobalMarketGate: heartbeat mode active — skipping MarketGrader start")
    else:
        start_grading_service()


# -----------------------------------------------------------------------------
# Signal receivers (GlobalMarkets -> ThorTrading)
# -----------------------------------------------------------------------------
@receiver(market_opened)
def handle_market_opened(sender, instance: Market, **kwargs):
    if not GLOBAL_TIMER_ENABLED:
        return
    if not _is_controlled_market(instance):
        _skip(f"{getattr(instance, 'country', '?')} not controlled")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("GlobalMarketGate: %s market OPEN", country)

    first_open = _register_open(country)

    # OPEN capture (only if enabled)
    if open_capture_allowed(instance):
        try:
            from ThorTrading.GlobalMarketGate.open_capture import capture_market_open

            capture_market_open(instance)
        except Exception:
            logger.exception("GlobalMarketGate: market-open capture failed for %s", country)
    else:
        _skip(f"open capture disabled for {country}")

    # Session tracking gate (no side-effects; supervisor self-manages)
    if not session_tracking_allowed(instance):
        _skip(f"session tracking disabled for {country}")

    # Grader start (only if NOT heartbeat mode)
    if _heartbeat_mode_active():
        logger.info("GlobalMarketGate: heartbeat mode active — skipping MarketGrader start")
    else:
        try:
            start_grading_service()
        except Exception:
            logger.exception("GlobalMarketGate: failed to start MarketGrader after %s open", country)

    if first_open:
        _start_global_background_services()


@receiver(market_closed)
def handle_market_closed(sender, instance: Market, **kwargs):
    if not GLOBAL_TIMER_ENABLED:
        return
    if not _is_controlled_market(instance):
        _skip(f"{getattr(instance, 'country', '?')} not controlled")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("GlobalMarketGate: %s market CLOSE", country)

    # CLOSE capture (only if enabled)
    if close_capture_allowed(instance):
        try:
            from ThorTrading.GlobalMarketGate.close_capture import capture_market_close

            result = capture_market_close(country)
            logger.info("GlobalMarketGate: close capture result %s => %s", country, result.get("status"))
        except Exception:
            logger.exception("GlobalMarketGate: market-close capture failed for %s", country)
    else:
        _skip(f"close capture disabled for {country}")

    last_close = _register_close(country)

    if last_close:
        _stop_global_background_services()

        if _heartbeat_mode_active():
            logger.info("GlobalMarketGate: heartbeat mode active — skipping MarketGrader stop")
        else:
            try:
                stop_grading_service()
            except Exception:
                logger.exception("GlobalMarketGate: failed to stop MarketGrader after %s close", country)


__all__ = [
    "GLOBAL_TIMER_ENABLED",
    "CONTROLLED_COUNTRIES",
    "market_enabled",
    "session_tracking_allowed",
    "open_capture_allowed",
    "close_capture_allowed",
    "bootstrap_open_markets",
    "handle_market_opened",
    "handle_market_closed",
]
