from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from Instruments.services.market_52w_live import seed_live_52w_all_symbols
from Instruments.services.market_52w_recompute import recompute_rolling_52w_from_24h


class Command(BaseCommand):
    help = "Recompute true rolling 52w highs/lows from MarketTrading24Hour history (fixes expired extremes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--asof",
            type=str,
            default=None,
            help="As-of date (UTC) in YYYY-MM-DD. Default: today (UTC).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Window size in days (inclusive). Default: 365.",
        )
        parser.add_argument(
            "--weeks",
            type=int,
            default=None,
            help="Alternative to --days. If provided, window_days = weeks*7.",
        )
        parser.add_argument(
            "--symbols",
            nargs="*",
            default=None,
            help="Optional list of symbols to recompute. Default: all tracked symbols.",
        )
        parser.add_argument(
            "--seed-redis",
            action="store_true",
            help="Also reseed live:52w:* from DB for the current UTC session_number after recompute.",
        )

    def handle(self, *args, **options):
        asof_raw = options.get("asof")
        days = options.get("days")
        weeks = options.get("weeks")
        symbols = options.get("symbols")
        seed_redis = bool(options.get("seed_redis"))

        if weeks is not None:
            days = int(weeks) * 7

        if asof_raw:
            asof_date = date.fromisoformat(asof_raw)
        else:
            asof_date = timezone.now().astimezone(timezone.utc).date()

        result = recompute_rolling_52w_from_24h(asof_date=asof_date, window_days=int(days), symbols=symbols)

        self.stdout.write(
            self.style.SUCCESS(
                "recompute_52w_stats done: "
                f"asof={result.asof_date} window_start={result.window_start} window_days={result.window_days} "
                f"symbols_seen={result.symbols_seen} updated={result.updated_rows} skipped_no_data={result.skipped_no_data}"
            )
        )

        if seed_redis:
            session_number = int(asof_date.strftime("%Y%m%d"))
            seeded = seed_live_52w_all_symbols(session_number=session_number)
            self.stdout.write(self.style.SUCCESS(f"Seeded Redis live 52w for session_number={session_number}: {seeded} symbols"))
