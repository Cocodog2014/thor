from __future__ import annotations

from django.core.management.base import BaseCommand



class Command(BaseCommand):
    help = "Deprecated (no-op): MarketSession grouping uses session_number now."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Nothing to do: MarketSession.capture_group was removed; session_number is the grouping key."
            )
        )

