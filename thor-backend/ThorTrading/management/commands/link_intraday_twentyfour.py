from __future__ import annotations
import logging
from typing import Dict, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.Market24h import MarketTrading24Hour
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


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
        batch_size: int = options["batch_size"]
        max_rows = options.get("max_rows")
        dry_run: bool = options.get("dry_run", False)
        create_missing: bool = options.get("create_missing", False)
        verbose: bool = options.get("verbose", False)

        qs = MarketIntraday.objects.filter(twentyfour__isnull=True).order_by("id")
        if max_rows:
            qs = qs[:max_rows]

        processed = 0
        linked = 0
        skipped_missing_parent = 0
        session_group_cache: Dict[str, int | None] = {}
        twentyfour_cache: Dict[Tuple[int, str], MarketTrading24Hour] = {}

        def resolve_session_group(country: str) -> int | None:
            if country in session_group_cache:
                return session_group_cache[country]
            sg = (
                MarketSession.objects.filter(country=country)
                .order_by("-session_number")
                .values_list("session_number", flat=True)
                .first()
            )
            session_group_cache[country] = sg
            return sg

        buffer = []

        for row in qs.iterator(chunk_size=batch_size):
            processed += 1
            country = normalize_country_code(row.country) or row.country
            symbol = (row.symbol or "").upper()
            if not symbol:
                continue

            sg = resolve_session_group(country)
            if sg is None:
                # Cannot link without a numeric session_number; skip
                continue

            cache_key = (sg, symbol)
            twentyfour = twentyfour_cache.get(cache_key)
            if twentyfour is None:
                if create_missing:
                    if dry_run:
                        twentyfour_cache[cache_key] = None  # marker to avoid recounting
                        continue
                    twentyfour, _ = MarketTrading24Hour.objects.get_or_create(
                        session_group=sg,
                        symbol=symbol,
                        defaults={
                            "session_date": row.timestamp_minute.date(),
                            "country": country,
                        },
                    )
                    twentyfour_cache[cache_key] = twentyfour
                else:
                    skipped_missing_parent += 1
                    continue

            row.twentyfour = twentyfour
            buffer.append(row)

            if len(buffer) >= batch_size:
                self._flush_buffer(buffer)
                linked += len(buffer)
                buffer.clear()

        if buffer:
            self._flush_buffer(buffer)
            linked += len(buffer)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run: processed={processed} linkable={linked} skipped_missing_parent={skipped_missing_parent}"
                )
            )
            return

        if verbose:
            self.stdout.write(
                f"Processed={processed} linked={linked} skipped_missing_parent={skipped_missing_parent}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed={processed} linked={linked} skipped_missing_parent={skipped_missing_parent} pending={max(processed - linked, 0)}"
            )
        )

    def _flush_buffer(self, rows):
        if not rows:
            return
        with transaction.atomic():
            MarketIntraday.objects.bulk_update(rows, ["twentyfour"])
