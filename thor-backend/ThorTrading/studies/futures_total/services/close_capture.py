from __future__ import annotations

import logging
from typing import Any, Dict

from GlobalMarkets.models.market_clock import Market
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.studies.futures_total.models.market_session import MarketSession
from GlobalMarkets.services import normalize_country_code
from ThorTrading.studies.futures_total.services.sessions.metrics import MarketCloseMetric, MarketRangeMetric
from ThorTrading.studies.futures_total.quotes import get_enriched_quotes_with_composite

logger = logging.getLogger(__name__)


def _latest_session_number(country: str | None):
    if not country:
        return None
    return (
        MarketSession.objects.filter(country=country)
        .order_by("-session_number")
        .values_list("session_number", flat=True)
        .first()
    )


def _resolve_session_number(country: str, session_number: int | None) -> int | None:
    if session_number is not None:
        return session_number
    return _latest_session_number(country)


def _base_payload(country: str | None) -> Dict[str, Any]:
    return {
        "country": country,
    }


def capture_market_close(country: str | None, force: bool = False) -> Dict[str, Any]:
    from ThorTrading.studies.futures_total.services.global_market_gate import close_capture_allowed

    payload = _base_payload(country)

    if not country:
        payload.update(
            {
                "status": "error",
                "message": "Country is required",
            }
        )
        return payload

    country = normalize_country_code(country) or country

    market = Market.objects.filter(country=country).first()
    if not market:
        payload.update(
            {
                "status": "unknown-market",
                "message": f"No GlobalMarkets market found for '{country}'",
            }
        )
        return payload

    if not close_capture_allowed(market):
        payload.update(
            {
                "status": "disabled",
                "message": "Close capture disabled for this market",
            }
        )
        return payload

    active_session_number = live_data_redis.get_active_session_number()
    latest_session_number = _resolve_session_number(country, active_session_number)

    if latest_session_number is None:
        payload.update(
            {
                "status": "no-sessions",
                "message": f"No sessions found for country '{country}'",
            }
        )
        return payload

    payload["session_number"] = active_session_number

    already_closed = MarketSession.objects.filter(
        country=country,
        session_number=latest_session_number,
        market_close__isnull=False,
    ).exists()

    if already_closed and not force:
        payload.update(
            {
                "status": "already-closed",
                "message": "Close metrics already populated; use force=True to recompute.",
            }
        )
        return payload

    try:
        enriched, _ = get_enriched_quotes_with_composite()
    except Exception as exc:
        logger.exception("Quote fetch failed for close capture: country=%s", country)
        payload.update(
            {
                "status": "error",
                "message": f"Quote fetch failed: {exc}",
            }
        )
        return payload

    country_rows = [
        r
        for r in enriched or []
        if (r.get("country") or r.get("instrument", {}).get("country")) == country
    ]

    try:
        close_updated = MarketCloseMetric.update_for_country_on_close(
            country,
            country_rows,
            session_number=latest_session_number,
        )
    except Exception as exc:
        logger.exception("MarketCloseMetric update failed for %s", country)
        payload.update(
            {
                "status": "error",
                "message": f"MarketCloseMetric error: {exc}",
            }
        )
        return payload

    try:
        range_updated = MarketRangeMetric.update_for_country_on_close(
            country,
            session_number=latest_session_number,
        )
    except Exception as exc:
        logger.exception("MarketRangeMetric update failed for %s", country)
        payload.update(
            {
                "status": "error",
                "message": f"MarketRangeMetric error: {exc}",
            }
        )
        return payload

    payload.update(
        {
            "status": "ok",
            "force": force,
            "close_rows_updated": close_updated,
            "range_rows_updated": range_updated,
        }
    )
    return payload


__all__ = [
    "capture_market_close",
]
