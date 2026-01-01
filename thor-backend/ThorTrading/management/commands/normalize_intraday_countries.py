from __future__ import annotations
from django.core.management.base import BaseCommand

from ThorTrading.studies.futures_total.command_logic.normalize_intraday_countries import run


class Command(BaseCommand):
    help = "Normalize country fields for intraday and market rows to canonical values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report changes without writing them.",
        )
        parser.add_argument("--verbose", action="store_true", help="Log counts as they accrue.")

    def handle(self, *args, **options):
        run(
            dry_run=bool(options.get("dry_run", False)),
            verbose=bool(options.get("verbose", False)),
            stdout=self.stdout,
            style=self.style,
        )
