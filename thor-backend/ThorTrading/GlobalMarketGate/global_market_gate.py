"""
Global Market Gate (ONE DOOR)

Purpose
-------
This module is the single "door" between the GlobalMarkets app and ThorTrading.

GlobalMarkets owns:
- Market status (OPEN/CLOSED)
- Signals: market_opened / market_closed

ThorTrading owns:
- Market-open capture (session snapshot rows)
- Market-close capture (close snapshots / 24h finalization hooks)
- Intraday supervisors (1m bars)
- Optional grading service (if NOT using heartbeat scheduler)

How it works
------------
1) GlobalMarkets fires market_opened / market_closed.
2) This module receives those signals and decides whether to run ThorTrading services.
3) We keep all gating logic + receivers in ONE file for consistency.

Enable/Disable
--------------
- THOR_USE_GLOBAL_MARKET_TIMER=1   (default on)  -> this gate runs on GlobalMarkets signals
- THOR_USE_GLOBAL_MARKET_TIMER=0                 -> gate does nothing

Scheduler mode
--------------
- THOR_SCHEDULER_MODE=heartbeat  -> grading start/stop is skipped (heartbeat owns jobs)
- THOR_SCHEDULER_MODE=legacy     -> this gate starts/stops grading service on first open / last close
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

# ✅ These functions were moved into ThorTrading/GlobalMarketGate/
from ThorTrading.GlobalMarketGate.open_capture import capture_market_open
from ThorTrading.GlobalMarketGate.close_capture import capture_market_close

from ThorTrading.services.intraday_supervisor import intraday_market_supervisor
from ThorTrading.services.sessions.grading import start_grading_service, stop_grading_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Feature flags / configuration
# ---------------------------------------------------------------------

GLOBAL_TIMER_ENABLED = os.environ.get("THOR_USE_GLOBAL_MARKET_TIMER", "1").lower() not in {
    "0",
    "false",
    "no",
}

CONTROLLED_COUNTRIES = set(CONTROL_COUNTRIES)

# Track currently open controlled markets (so we can start/stop “global” services once)
_ACTIVE_COUNTRIES: Set[str] = set()
_ACTIVE_LOCK = threading.RLock()


def _heartbeat_mode_active() -> bool:
    """True when heartbeat scheduler is the source of truth for background jobs."""
    return os.environ.get("THOR_SCHEDULER_MODE", "heartbeat").lower() == "heartbeat"


# ---------------------------------------------------------------------
# Gate logic: decide if ThorTrading should act on this market event
# ---------------------------------------------------------------------

def _is_controlled_market(market: Market | None) -> bool:
    """Only act on active markets that are in our CONTROLLED_COUNTRIES set."""
    if market is None or not getattr(market, "is_active", False):
        return False

    normalized = normalize_country_code(getattr(market, "country", None))
    if normalized and normalized in CONTROLLED_COUNTRIES:
        return True

    # Fallback: raw value
    raw = getattr(market, "country", None)
    return raw in CONTROLLED_COUNTRIES if raw else False


def _skip_reason(reason: str) -> None:
    logger.debug("GlobalMarketGate skipped: %s", reason)


def _register_open(country: str) -> bool:
    """
    Track an open country.
    Returns True if this was the FIRST open country (transition empty -> non-empty).
    """
    with _ACTIVE_LOCK:
        was_empty = not _ACTIVE_COUNTRIES
        _ACTIVE_COUNTRIES.add(country)
        return was_empty


def _register_close(country: str) -> bool:
    """
    Track a close country.
    Returns True if this was the LAST open country (transition non-empty -> empty).
    """
    with _ACTIVE_LOCK:
        was_member = country in _ACTIVE_COUNTRIES
        if was_member:
            _ACTIVE_COUNTRIES.remove(country)
        return was_member and not _ACTIVE_COUNTRIES


# ---------------------------------------------------------------------
# Optional global services (placeholders; heartbeat owns most of these now)
# ---------------------------------------------------------------------

def _start_global_background_services() -> None:
    """
    Any “global once-per-day” or “global while-any-market-open” services can start here.
    NOTE: 52-week and VWAP are handled as heartbeat jobs now, so we keep this minimal.
    """
    logger.debug("GlobalMarketGate: global background services start (currently none)")


def _stop_global_background_services() -> None:
    """Stop anything started in _start_global_background_services()."""
    logger.debug("GlobalMarketGate: global background services stop (currently none)")


# ---------------------------------------------------------------------
# Bootstrap: if process starts and some markets are already open
# ---------------------------------------------------------------------

def bootstrap_open_markets() -> None:
    """
    Call this once at app startup to ensure ThorTrading is “caught up”
    if the server restarts while a market is already OPEN.
    """
    if not GLOBAL_TIMER_ENABLED:
        return

    try:
        open_markets = Market.objects.filter(is_active=True, status="OPEN")
    except Exception:
        logger.exception("GlobalMarketGate: failed to bootstrap open markets")
        return

    controlled = [m for m in open_markets if _is_controlled_market(m)]
    if not controlled:
        return

    logger.info("GlobalMarketGate: bootstrapping %s open market(s)", len(controlled))

    for market in controlled:
        country = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)

        _register_open(country)

        # Start intraday supervisor (bars)
        try:
            intraday_market_supervisor.on_market_open(market)
        except Exception:
            logger.exception("GlobalMarketGate: intraday bootstrap failed for %s", country)

    _start_global_background_services()

    # Only start grader if NOT using heartbeat scheduler
    if _heartbeat_mode_active():
        logger.info("GlobalMarketGate: skipping MarketGrader start (heartbeat scheduler active)")
    else:
        try:
            start_grading_service()
        except Exception:
            logger.exception("GlobalMarketGate: failed to start MarketGrader during bootstrap")


# ---------------------------------------------------------------------
# Signal receivers (GlobalMarkets -> ThorTrading)
# ---------------------------------------------------------------------

@receiver(market_opened)
def handle_market_opened(sender, instance: Market, **kwargs) -> None:
    """
    On market open:
      - capture_market_open(instance)
      - start intraday supervisor
      - start grader if legacy mode and first open
    """
    if not GLOBAL_TIMER_ENABLED:
        return

    if not _is_controlled_market(instance):
        _skip_reason(f"market {getattr(instance, 'country', '?')} not controlled or inactive")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("GlobalMarketGate: detected %s market OPEN", country)

    first_open = _register_open(country)

    # 1) Capture market-open snapshot rows
    try:
        capture_market_open(instance)
    except Exception:
        logger.exception("GlobalMarketGate: market-open capture failed for %s", country)

    # 2) Start intraday bar supervisor for this market
    try:
        intraday_market_supervisor.on_market_open(instance)
    except Exception:
        logger.exception("GlobalMarketGate: failed to start intraday supervisor for %s", country)

    # 3) Start optional services
    if first_open:
        _start_global_background_services()

    if _heartbeat_mode_active():
        logger.info("GlobalMarketGate: skipping MarketGrader start (heartbeat scheduler active)")
    else:
        try:
            start_grading_service()
        except Exception:
            logger.exception("GlobalMarketGate: failed to start MarketGrader after %s open", country)


@receiver(market_closed)
def handle_market_closed(sender, instance: Market, **kwargs) -> None:
    """
    On market close:
      - capture_market_close(country)
      - stop intraday supervisor
      - stop grader if legacy mode and last close
    """
    if not GLOBAL_TIMER_ENABLED:
        return

    if not _is_controlled_market(instance):
        _skip_reason(f"market {getattr(instance, 'country', '?')} not controlled or inactive")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("GlobalMarketGate: detected %s market CLOSE", country)

    # 1) Capture close snapshot / finalize logic
    try:
        result = capture_market_close(country)
        logger.info("GlobalMarketGate: market-close capture result for %s: %s", country, result.get("status"))
    except Exception:
        logger.exception("GlobalMarketGate: market-close capture failed for %s", country)

    # 2) Stop intraday bar supervisor for this market
    try:
        intraday_market_supervisor.on_market_close(instance)
    except Exception:
        logger.exception("GlobalMarketGate: failed to stop intraday supervisor for %s", country)

    last_close = _register_close(country)

    # 3) Stop optional services if last controlled market closed
    if last_close:
        _stop_global_background_services()

        if _heartbeat_mode_active():
            logger.info("GlobalMarketGate: skipping MarketGrader stop (heartbeat scheduler active)")
        else:
            try:
                stop_grading_service()
            except Exception:
                logger.exception("GlobalMarketGate: failed to stop MarketGrader after %s close", country)


__all__ = [
    "GLOBAL_TIMER_ENABLED",
    "CONTROLLED_COUNTRIES",
    "bootstrap_open_markets",
    "handle_market_opened",
    "handle_market_closed",
]
