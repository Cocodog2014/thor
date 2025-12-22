import logging
from django.utils import timezone
from GlobalMarkets.models.market import Market
from GlobalMarkets.models.us_status import USMarketStatus

logger = logging.getLogger(__name__)


def reconcile_market_statuses(*, ctx=None) -> dict:
    """Heartbeat job: single source of truth for Market.status."""
    us_open = USMarketStatus.is_us_market_open_today()
    markets = Market.objects.filter(is_active=True, is_control_market=True)

    changed = 0
    checked = 0
    for market in markets:
        checked += 1
        target = "OPEN" if us_open and market.is_market_open_now() else "CLOSED"

        if market.status != target:
            previous = market.status
            market.status = target
            market.save()
            changed += 1
            logger.info("GM status flip %s: %s -> %s", market.country, previous, target)

    return {
        "ts": timezone.now().isoformat(),
        "us_open": us_open,
        "checked": checked,
        "changed": changed,
    }


class ReconcileMarketStatusesJob:
    """Job wrapper for the heartbeat registry."""

    name = "gm.reconcile_status"

    def run(self, ctx=None) -> None:  # ctx kept for registry signature
        reconcile_market_statuses(ctx=ctx)
