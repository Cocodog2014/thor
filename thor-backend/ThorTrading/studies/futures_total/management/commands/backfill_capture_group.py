from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deprecated (no-op): MarketSession grouping uses session_number now."

    def handle(self, *args, **options):
        from ThorTrading.studies.futures_total.command_logic.backfill_capture_group import run

        run(stdout=self.stdout, style=self.style)
