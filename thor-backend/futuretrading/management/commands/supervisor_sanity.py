from django.core.management.base import BaseCommand
from django.utils import timezone

from FutureTrading.services.IntradayMarketSupervisor import IntradayMarketSupervisor
from FutureTrading.models.MarketSession import MarketSession


class Command(BaseCommand):
    help = "Run a one-shot sanity check for IntradayMarketSupervisor logging and counters"

    def handle(self, *args, **options):
        supervisor = IntradayMarketSupervisor()

        # Craft a minimal enriched row resembling the enrichment pipeline output.
        # Keys expected by _update_24h_and_intraday: 'future', 'last', 'volume', 'timestamp'
        now = timezone.now()
        enriched_rows = [
            {
                'future': 'ES',
                'last': 4750.25,
                'volume': 3,
                'timestamp': now,
            }
        ]

        # Country can be 'USA' to align with typical MarketSession setup
        country = 'USA'

        # Ensure a MarketSession exists so latest capture_group resolves
        # Use latest existing session for the country; update capture_group to a sanity tag
        session = (
            MarketSession.objects.filter(country=country)
            .order_by('-captured_at')
            .first()
        )
        if session is None:
            self.stdout.write(self.style.WARNING("No MarketSession found for country; create one via your normal open capture flow."))
            return

        counts = supervisor._update_24h_and_intraday(country, enriched_rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sanity complete → 24h-updated={counts.get('twentyfour_updates',0)}, "
                f"intraday-bars={counts.get('intraday_bars',0)}, "
                f"session-volume-updates={counts.get('session_volume_updates',0)}"
            )
        )
