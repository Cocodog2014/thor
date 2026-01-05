from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
	help = (
		"Inspect MarketSession row counts and detect true duplicates. "
		"True duplicates are rows sharing (country, session_number, capture_kind, symbol)."
	)

	def add_arguments(self, parser):
		parser.add_argument("--limit", type=int, default=25, help="Max rows to show for each report.")
		parser.add_argument(
			"--kind",
			type=str,
			default="OPEN",
			help="Capture kind to summarize (default: OPEN).",
		)

	def handle(self, *args, **options):
		from ThorTrading.models import MarketSession

		limit: int = options["limit"]
		kind: str = str(options["kind"] or "OPEN").upper()

		self.stdout.write(self.style.MIGRATE_HEADING(f"MarketSession summary for capture_kind={kind}"))

		# Expected aggregation: one row per symbol; so counts per (country, session_number, capture_kind)
		# indicate how many symbols were captured for that session.
		expected = (
			MarketSession.objects.filter(capture_kind=kind)
			.values("country", "session_number", "capture_kind")
			.annotate(n=Count("id"))
			.order_by("-n")[:limit]
		)
		self.stdout.write("\nTop sessions by row-count (expected: roughly number of symbols captured):")
		self.stdout.write(str(list(expected)))

		# True duplicates: same country/session/kind/symbol multiple times.
		dupes = (
			MarketSession.objects.filter(capture_kind=kind)
			.values("country", "session_number", "capture_kind", "symbol")
			.annotate(n=Count("id"))
			.filter(n__gt=1)
			.order_by("-n")[:limit]
		)
		self.stdout.write("\nTrue duplicates (should be empty; indicates repeated inserts):")
		self.stdout.write(str(list(dupes)))
