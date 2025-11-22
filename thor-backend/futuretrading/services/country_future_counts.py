from collections import defaultdict
from django.db.models import Count
from django.utils import timezone

from FutureTrading.models.MarketSession import MarketSession


def get_country_future_counts():
    """
    Pure calculation:
    Returns nested dict like:
    {
        "Japan": {"TOTAL": 10, "ZB": 5, "DX": 5},
        "US": {"TOTAL": 30, "ES": 15, "NQ": 15},
        ...
    }
    """
    qs = (
        MarketSession.objects
        .values("country", "future")
        .annotate(total=Count("id"))
    )

    result = defaultdict(dict)
    for row in qs:
        result[row["country"]][row["future"]] = row["total"]
    return result


def update_country_future_stats():
    """Aggregate latest capture counts per country/future for monitoring.

    Today we simply recompute the counts and log them so operations can
    see that the dataset stayed balanced. In the future this hook can be
    extended to write into Redis or a reporting table for the frontend.
    """
    data = get_country_future_counts()

    # Optional: log it so we can see it happening during dev
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Updated country/future stats at %s", timezone.now())
    for country, futures in sorted(data.items()):
        logger.info("Country: %s", country)
        for future, count in sorted(futures.items()):
            logger.info("  %s : %s", future, count)