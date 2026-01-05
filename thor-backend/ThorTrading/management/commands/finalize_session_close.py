from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ThorTrading.studies.futures_total.command_logic.finalize_session_close import run


class Command(BaseCommand):
	help = (
		"Copy 24h close from MarketTrading24Hour into MarketSession.close_24h at session close. "
		"Requires --country and --symbol (instrument code). Optionally --session_number to override latest."
	)

	def add_arguments(self, parser):
		parser.add_argument('--country', required=True, help='Country code, e.g., USA, Japan, London')
		parser.add_argument('--symbol', required=True, help='Instrument code, e.g., ES, NQ, CL')
		parser.add_argument('--session_number', type=int, help='Numeric session_number to use; defaults to latest for country')
		parser.add_argument('--dry-run', action='store_true', help='Report the intended update without writing.')

	def handle(self, *args, **options):
		try:
			run(
				country=options["country"],
				symbol=options["symbol"],
				session_number=options.get("session_number"),
				dry_run=bool(options.get("dry_run", False)),
				stdout=self.stdout,
				style=self.style,
			)
		except ValueError as exc:
			raise CommandError(str(exc))

