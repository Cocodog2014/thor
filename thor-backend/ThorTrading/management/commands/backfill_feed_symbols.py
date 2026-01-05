from __future__ import annotations

from django.core.management.base import BaseCommand

from ThorTrading.studies.futures_total.command_logic.backfill_feed_symbols import run


class Command(BaseCommand):
	help = "Backfill feed_symbol for instruments and normalize canonical symbol when safe."

	def add_arguments(self, parser):
		parser.add_argument("--dry-run", action="store_true", help="Report changes without writing them")
		parser.add_argument("--batch-size", type=int, default=1000, help="Rows to scan per chunk (default: 1000)")
		parser.add_argument("--verbose", action="store_true", help="Log progress per batch")

	def handle(self, *args, **options):
		run(
			dry_run=bool(options.get("dry_run", False)),
			batch_size=int(options.get("batch_size", 1000)),
			verbose=bool(options.get("verbose", False)),
			stdout=self.stdout,
			style=self.style,
		)
