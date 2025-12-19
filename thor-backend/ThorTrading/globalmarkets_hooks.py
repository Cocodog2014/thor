"""Signal receivers that let GlobalMarkets orchestrate ThorTrading services."""

from __future__ import annotations

import logging
import os
import threading
from typing import Set

from django.dispatch import receiver

from GlobalMarkets.models.market import Market
from GlobalMarkets.signals import market_opened, market_closed

from ThorTrading.services.MarketCloseCapture import capture_market_close
from ThorTrading.services.MarketOpenCapture import capture_market_open
from ThorTrading.services.intraday_supervisor import intraday_market_supervisor
from ThorTrading.services.vwap_capture import (
    start_vwap_capture_service,
    stop_vwap_capture_service,
)
from ThorTrading.services.Week52Supervisor import (
    start_52w_monitor_supervisor,
    stop_52w_monitor_supervisor,
)
from ThorTrading.views.MarketGrader import start_grading_service, stop_grading_service
from ThorTrading.services.country_codes import normalize_country_code

logger = logging.getLogger(__name__)

GLOBAL_TIMER_ENABLED = os.environ.get("THOR_USE_GLOBAL_MARKET_TIMER", "1").lower() not in {
    "0",
    "false",
    "no",
}
CONTROLLED_COUNTRIES = {"USA", "Pre_USA", "Japan", "China", "India", "United Kingdom"}

_ACTIVE_COUNTRIES: Set[str] = set()
_ACTIVE_LOCK = threading.RLock()


def _is_controlled_market(market: Market | None) -> bool:
    if market is None or not market.is_active:
        return False

    normalized = normalize_country_code(getattr(market, "country", None))
    if normalized and normalized in CONTROLLED_COUNTRIES:
        return True

    country = getattr(market, "country", None)
    return country in CONTROLLED_COUNTRIES if country else False


def _skip_reason(reason: str):
    logger.debug("Global timer hook skipped: %s", reason)


def _register_open(country: str) -> bool:
    with _ACTIVE_LOCK:
        was_empty = not _ACTIVE_COUNTRIES
        _ACTIVE_COUNTRIES.add(country)
        return was_empty


def _register_close(country: str) -> bool:
    with _ACTIVE_LOCK:
        was_member = country in _ACTIVE_COUNTRIES
        if was_member:
            _ACTIVE_COUNTRIES.remove(country)
        return was_member and not _ACTIVE_COUNTRIES


def _start_global_background_services():
    start_vwap_capture_service()
    try:
        start_52w_monitor_supervisor()
    except Exception:
        logger.exception("Failed to start 52-week monitor supervisor")


def _stop_global_background_services():
    stop_vwap_capture_service()
    try:
        stop_52w_monitor_supervisor()
    except Exception:
        logger.exception("Failed to stop 52-week monitor supervisor")


def bootstrap_open_markets():
    """Start workers for markets already open at process start."""
    if not GLOBAL_TIMER_ENABLED:
        return
    try:
        open_markets = Market.objects.filter(
            is_active=True,
            is_control_market=True,
            status="OPEN",
        )
    except Exception:
        logger.exception("Failed to bootstrap open markets")
        return

    controlled = [m for m in open_markets if _is_controlled_market(m)]
    if not controlled:
        return

    logger.info("Bootstrapping global timer workers for %s open market(s)", len(controlled))
    for market in controlled:
        country = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
        _register_open(country)
        try:
            intraday_market_supervisor.on_market_open(market)
        except Exception:
            logger.exception("Intraday bootstrap failed for %s", country)

    _start_global_background_services()
    start_grading_service()


@receiver(market_opened)
def handle_market_opened(sender, instance: Market, **kwargs):
    if not GLOBAL_TIMER_ENABLED:
        return
    if not _is_controlled_market(instance):
        _skip_reason(f"market {getattr(instance, 'country', '?')} not controlled")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("Global timer detected %s market open.", country)

    first_open = _register_open(country)

    try:
        capture_market_open(instance)
    except Exception:
        logger.exception("Global timer market-open capture failed for %s", country)

    try:
        intraday_market_supervisor.on_market_open(instance)
    except Exception:
        logger.exception("Failed to start intraday supervisor for %s", country)

    try:
        start_grading_service()
    except Exception:
        logger.exception("Failed to start MarketGrader after %s open", country)

    if first_open:
        _start_global_background_services()


@receiver(market_closed)
def handle_market_closed(sender, instance: Market, **kwargs):
    if not GLOBAL_TIMER_ENABLED:
        return
    if not _is_controlled_market(instance):
        _skip_reason(f"market {getattr(instance, 'country', '?')} not controlled")
        return

    country = normalize_country_code(getattr(instance, "country", None)) or instance.country
    logger.info("Global timer detected %s market close.", country)

    try:
        result = capture_market_close(country)
        logger.info("Market close capture result for %s: %s", country, result.get("status"))
    except Exception:
        logger.exception("Global timer market-close capture failed for %s", country)

    try:
        intraday_market_supervisor.on_market_close(instance)
    except Exception:
        logger.exception("Failed to stop intraday supervisor for %s", country)

    last_close = _register_close(country)

    if last_close:
        _stop_global_background_services()
        try:
            stop_grading_service()
        except Exception:
            logger.exception("Failed to stop MarketGrader after %s close", country)


__all__ = [
    "GLOBAL_TIMER_ENABLED",
    "CONTROLLED_COUNTRIES",
    "handle_market_opened",
    "handle_market_closed",
    "bootstrap_open_markets",
]
