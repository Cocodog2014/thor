# FutureTrading/services/country_future_wndw_counts.py

"""
Computes and stores the sum of outcome metrics per (country, future) pair
into MarketSession.country_future_wndw_total.

For each (country, future), we sum the nine non-percentage columns:
  strong_buy_worked, strong_buy_didnt_work,
  buy_worked, buy_didnt_work,
  hold,
  strong_sell_worked, strong_sell_didnt_work,
  sell_worked, sell_didnt_work

and write that total (as a whole number) into country_future_wndw_total
for every row belonging to that (country, future) pair.

This service is intended to be called after market-open capture.
"""

from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from FutureTrading.models.MarketSession import MarketSession


def update_country_future_wndw_total():
    """Populate country_future_wndw_total with the sum of outcome columns."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Updating country_future_wndw_total at %s", timezone.now())

    # Reset all to 0 so unmatched pairs don't keep stale data
    MarketSession.objects.update(country_future_wndw_total=0)

    # Aggregate the sum of the nine outcome columns per (country, future)
    qs = (
        MarketSession.objects
        .values("country", "future")
        .annotate(
            total=Sum(
                Coalesce(F("strong_buy_worked"), Value(0))
                + Coalesce(F("strong_buy_didnt_work"), Value(0))
                + Coalesce(F("buy_worked"), Value(0))
                + Coalesce(F("buy_didnt_work"), Value(0))
                + Coalesce(F("hold"), Value(0))
                + Coalesce(F("strong_sell_worked"), Value(0))
                + Coalesce(F("strong_sell_didnt_work"), Value(0))
                + Coalesce(F("sell_worked"), Value(0))
                + Coalesce(F("sell_didnt_work"), Value(0))
            )
        )
    )

    updated_pairs = 0
    for row in qs:
        country = row["country"]
        future = row["future"]
        total = int(row["total"] or 0)

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
