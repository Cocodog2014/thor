"""Market close capture service shared by API and GlobalMarkets hooks."""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.db.models import Max

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.market_metrics import (
    MarketCloseMetric,
    MarketRangeMetric,
)

logger = logging.getLogger(__name__)


def _base_payload(country: str | None) -> Dict[str, Any]:
    return {
        "country": country,
    }


def capture_market_close(country: str | None, force: bool = False) -> Dict[str, Any]:
    """Finalize close + range metrics for the latest session of a country."""
    payload = _base_payload(country)

    if not country:
        payload.update(
            {
                "status": "error",
                "message": "Country is required",
            }
        )
        return payload

    latest_session = (
        MarketSession.objects.filter(country=country)
        .aggregate(Max("session_number"))
        .get("session_number__max")
    )

    if latest_session is None:
        payload.update(
            {
                "status": "no-sessions",
                "message": f"No sessions found for country '{country}'",
            }
        )
        return payload

    payload["session_number"] = latest_session

    already_closed = MarketSession.objects.filter(
        country=country,
        session_number=latest_session,
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
    except Exception as exc:  # pragma: no cover - defensive against feed failures
        logger.exception("Quote fetch failed for close capture: country=%s", country)
        payload.update(
            {
                "status": "error",
                "message": f"Quote fetch failed: {exc}",
            }
        )
        return payload

    try:
        close_updated = MarketCloseMetric.update_for_country_on_close(country, enriched)
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
