"""Market close capture service shared by API and GlobalMarkets hooks."""

from __future__ import annotations

import logging
from typing import Any, Dict

from GlobalMarkets.models.market import Market
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.sessions.global_market_gate import close_capture_allowed
from ThorTrading.services.sessions.metrics import (
    MarketCloseMetric,
    MarketRangeMetric,
)

logger = logging.getLogger(__name__)


def _latest_capture_group(country: str | None):
    if not country:
        return None
    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )


def _base_payload(country: str | None) -> Dict[str, Any]:
    return {
        "country": country,
    }


def capture_market_close(country: str | None, force: bool = False) -> Dict[str, Any]:
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

    latest_group = _latest_capture_group(country)

    if latest_group is None:
        payload.update(
            {
                "status": "no-sessions",
                "message": f"No sessions found for country '{country}'",
            }
        )
        return payload

    payload["capture_group"] = latest_group

    already_closed = MarketSession.objects.filter(
        country=country,
        capture_group=latest_group,
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
        close_updated = MarketCloseMetric.update_for_country_on_close(country, country_rows)
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
        range_updated = MarketRangeMetric.update_for_country_on_close(country)
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


__all__ = ["capture_market_close"]
