# FutureTrading/services/country_future_wndw_total.py

"""
Computes and stores the total number of WNDW-bearing rows per
(country, future) pair into MarketSession.country_future_wndw_total.

"WNDW-bearing rows" means:
- wndw is not null
- wndw is not empty
- ANY value counts (BUY, STRONG_BUY, NEUTRAL, SELL, STRONG_SELL, etc.)

This service is intended to be called after market-open capture.
"""

from django.db.models import Count
from django.utils import timezone
from FutureTrading.models.MarketSession import MarketSession


def update_country_future_wndw_total():
    """Populate country_future_wndw_total for every (country, future)."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Updating country_future_wndw_total at %s", timezone.now())

    # ---------------------------------------------------------
    # Reset all values to 0 so unmatched pairs don't keep old data
    # ---------------------------------------------------------
    MarketSession.objects.update(country_future_wndw_total=0)

    # ---------------------------------------------------------
    # Count only rows where WNDW has any value
    # ---------------------------------------------------------
    qs = (
        MarketSession.objects
        .exclude(wndw__isnull=True)
        .exclude(wndw="")
        .values("country", "future")
        .annotate(total=Count("id"))
    )

    updated_pairs = 0
    for row in qs:
        country = row["country"]
        future = row["future"]
        total = row["total"]

        updated = (
            MarketSession.objects
            .filter(country=country, future=future)
            .update(country_future_wndw_total=total)
        )

        updated_pairs += 1
        logger.info(
            "Set country_future_wndw_total=%s on %s rows for %s / %s",
            total,
            updated,
            country,
            future,
        )

    logger.info(
        "country_future_wndw_total refresh complete: %s (country, future) pairs updated",
        updated_pairs,
    )
