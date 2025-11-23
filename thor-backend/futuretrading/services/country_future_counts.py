from django.db.models import Count
from django.utils import timezone

from FutureTrading.models.MarketSession import MarketSession


def update_country_future_stats():
    """Persist counts per (country, future) pair into `country_future`.

    Every invocation recalculates how many MarketSession rows exist for each
    (country, future) combination and writes that number to the
    `country_future` column across all matching rows. Downstream dashboards can
    then read the count from any row without doing their own aggregation.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Updating country_future counts at %s", timezone.now())

    qs = (
        MarketSession.objects
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
            .update(country_future=total)
        )

        updated_pairs += 1
        logger.info(
            "Set country_future=%s on %s rows for %s / %s",
            total,
            updated,
            country,
            future,
        )

    logger.info(
        "country_future stats refresh complete: %s (country, future) pairs updated",
        updated_pairs,
    )