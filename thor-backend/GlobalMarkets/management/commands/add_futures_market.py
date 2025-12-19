"""Management command to add the CME Futures (GLOBEX) control market."""
from django.core.management.base import BaseCommand
from GlobalMarkets.models.market import Market


class Command(BaseCommand):
    help = "Add the CME Futures (GLOBEX) control market for intraday session gating"

    def handle(self, *args, **options):
        # Check if it already exists
        futures_market = Market.objects.filter(country="Futures").first()
        
        if futures_market:
            self.stdout.write(
                self.style.WARNING(
                    f"✅ Futures market already exists: {futures_market}"
                )
            )
            return

        # Create the Futures market
        futures_market = Market.objects.create(
            country="Futures",
            timezone_name="America/Chicago",
            market_open_time="17:00",  # 5 PM CT Sunday
            market_close_time="17:00",  # 5 PM CT Friday
            status="CLOSED",  # MarketMonitor will manage it
            is_control_market=True,
            is_active=True,
            enable_futures_capture=True,
            enable_open_capture=True,
            enable_close_capture=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Futures market: {futures_market}\n"
                f"   Timezone: America/Chicago\n"
                f"   Session: Sun 5 PM CT → Fri 5 PM CT\n"
                f"   MarketMonitor will manage status=OPEN/CLOSED"
            )
        )
