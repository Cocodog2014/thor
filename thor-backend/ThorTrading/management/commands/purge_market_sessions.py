from __future__ import annotations

"""Delete all MarketSession rows. Use with caution.

Usage:
  python manage.py purge_market_sessions --yes-i-am-sure
"""

from django.core.management.base import BaseCommand, CommandError

from ThorTrading.studies.futures_total.command_logic.purge_market_sessions import run


class Command(BaseCommand):
	help = "Delete ALL MarketSession rows (single-table design)."

	def add_arguments(self, parser):
		parser.add_argument('--yes-i-am-sure', action='store_true', help='Confirm destructive operation')
		parser.add_argument('--dry-run', action='store_true', help='Show how many rows would be deleted and exit')
		parser.add_argument(
			'--confirm',
			type=str,
			help="Additional confirmation token. Must be 'DELETE' to proceed.",
		)

	def handle(self, *args, **options):
		try:
			run(
				dry_run=bool(options.get("dry_run")),
				yes_i_am_sure=bool(options.get("yes_i_am_sure")),
				confirm=options.get("confirm"),
				stdout=self.stdout,
				style=self.style,
			)
		except ValueError as exc:
			raise CommandError(str(exc))

