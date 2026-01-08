import logging
from django.utils import timezone
from GlobalMarkets.models.market import Market

logger = logging.getLogger(__name__)


def reconcile_market_statuses(*, ctx=None) -> dict:
    """Heartbeat job: single source of truth for Market.status."""
    markets = Market.objects.filter(is_active=True)

    changed = 0
    checked = 0
    for market in markets:
        checked += 1
        status = None
        try:
            status = market.get_market_status()
        except Exception as exc:
            logger.debug("Market status compute failed for %s: %s", market.country, exc)

        if isinstance(status, dict):
            target = status.get("status") or ("OPEN" if status.get("is_in_trading_hours") else "CLOSED")
        else:
            target = "OPEN" if market.is_market_open_now() else "CLOSED"

        if market.status != target:
            previous = market.status
            market.status = target
            market.save()
            changed += 1
            logger.info("GM status flip %s: %s -> %s", market.country, previous, target)

    return {
        "ts": timezone.now().isoformat(),
        "checked": checked,
        "changed": changed,
    }


class ReconcileMarketStatusesJob:
    """Job wrapper for the heartbeat registry."""

    name = "gm.reconcile_status"

    def run(self, ctx=None) -> None:  # ctx kept for registry signature
        reconcile_market_statuses(ctx=ctx)
