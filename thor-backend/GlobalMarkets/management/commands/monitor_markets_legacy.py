"""
Management command to reconcile global market status ONCE.

⚠️ IMPORTANT:
This command DOES NOT run continuously.
It contains NO timers, NO loops, and NO scheduling.

All recurring scheduling MUST be handled by:
    thor_project/realtime heartbeat jobs

This command exists ONLY for:
- manual reconciliation
- debugging
- admin-triggered correction

Usage:
    python manage.py monitor_markets
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from GlobalMarkets.models.market_clock import Market
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run a one-time reconciliation of global market status"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🌍 Global Markets Reconcile (RUN ONCE)"))
        self.stdout.write(f"Timestamp: {timezone.now().isoformat()}")
        self.stdout.write("-" * 60)

        self.reconcile_markets()

        self.stdout.write(self.style.SUCCESS("\n✅ Reconciliation complete"))

    def reconcile_markets(self):
        """Run a single reconciliation pass for all active control markets"""

        markets = Market.objects.filter(is_active=True)

        for market in markets:
            self.reconcile_market(market)

    def reconcile_market(self, market):
        """Reconcile one market's OPEN/CLOSED status"""

        status_data = None
        try:
            status_data = market.get_market_status()
        except Exception as exc:
            logger.debug("Market status compute failed for %s: %s", market.country, exc)

        if isinstance(status_data, dict):
            target_status = status_data.get("status") or ("OPEN" if status_data.get("is_in_trading_hours") else "CLOSED")
        else:
            target_status = "OPEN" if market.is_market_open_now() else "CLOSED"

        current_status = market.status

        if current_status != target_status:
            self.stdout.write(
                self.style.WARNING(
                    f"🔄 {market.country:15} | {current_status} → {target_status}"
                )
            )

            market.status = target_status
            market.save()  # emits signals

            self.stdout.write(
                self.style.SUCCESS(
                    f"   └─ Status updated (signal emitted)"
                )
            )
        else:
            status_icon = "🟢" if target_status == "OPEN" else "🔴"
            market_status = status_data if isinstance(status_data, dict) else {}
            next_event = market_status.get("next_event", "n/a")
            seconds = market_status.get("seconds_to_next_event", 0)

            minutes = seconds // 60
            self.stdout.write(
                f"{status_icon} {market.country:15} | {target_status:6} | "
                f"Next {next_event} in {minutes}m"
            )
