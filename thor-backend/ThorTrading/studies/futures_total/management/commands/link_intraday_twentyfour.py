from __future__ import annotations

from django.core.management.base import BaseCommand

from ThorTrading.studies.futures_total.command_logic.link_intraday_twentyfour import run


class Command(BaseCommand):
    help = "Attach missing MarketTrading24Hour parents to MarketIntraday rows where twentyfour is NULL."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500, help="Rows to process per bulk update.")
        parser.add_argument(
            "--max-rows",
            type=int,
            default=None,
            help="Optional cap on rows to process (for testing).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report actions without writing.")
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create MarketTrading24Hour rows if missing; otherwise skip linking.",
        )
        parser.add_argument("--verbose", action="store_true", help="Log per-batch progress.")

    def handle(self, *args, **options):
        run(
            batch_size=int(options["batch_size"]),
            max_rows=options.get("max_rows"),
            dry_run=bool(options.get("dry_run", False)),
            create_missing=bool(options.get("create_missing", False)),
            verbose=bool(options.get("verbose", False)),
            stdout=self.stdout,
            style=self.style,
        )
