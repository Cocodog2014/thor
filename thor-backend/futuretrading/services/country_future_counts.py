from django.db.models import Count
from django.utils import timezone

from FutureTrading.models.MarketSession import MarketSession


def update_country_future_stats():
    """DEPRECATED: No longer needed. country_future is now set on insert as an incrementing counter.
    
    This function previously performed bulk updates that overwrote country_future for all rows,
    preventing it from being a historical session counter. It's now a no-op to avoid breaking
    any external code that may still reference it.
    
    Old behavior: Recalculated total count for each (country, future) pair and bulk-updated all rows.
    New behavior: country_future is set once on MarketSession creation and never modified.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(
        "update_country_future_stats() called but is deprecated (no-op). "
        "country_future is now set on insert and never updated."
    )