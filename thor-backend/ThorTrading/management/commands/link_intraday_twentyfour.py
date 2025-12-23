import logging
from typing import Dict, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.Martket24h import FutureTrading24Hour
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Attach missing FutureTrading24Hour parents to MarketIntraday rows where twentyfour is NULL."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500, help="Rows to process per bulk update.")
        parser.add_argument(
            "--max-rows",
            type=int,
            default=None,
            help="Optional cap on rows to process (for testing).",
        )

    def handle(self, *args, **options):
        batch_size: int = options["batch_size"]
        max_rows = options.get("max_rows")

        qs = MarketIntraday.objects.filter(twentyfour__isnull=True).order_by("id")
        if max_rows:
            qs = qs[:max_rows]

        processed = 0
        linked = 0
        session_group_cache: Dict[str, int | None] = {}
        twentyfour_cache: Dict[Tuple[int, str], FutureTrading24Hour] = {}

        def resolve_session_group(country: str) -> int | None:
            if country in session_group_cache:
                return session_group_cache[country]
            sg = (
                MarketSession.objects.filter(country=country)
                .exclude(capture_group__isnull=True)
                .order_by("-capture_group")
                .values_list("capture_group", flat=True)
                .first()
            )
            session_group_cache[country] = sg
            return sg

        buffer = []

        for row in qs.iterator(chunk_size=batch_size):
            processed += 1
            country = normalize_country_code(row.country) or row.country
            future = (row.future or "").upper()
            if not future:
                continue

            sg = resolve_session_group(country)
            if sg is None:
                # Cannot link without a numeric capture_group; skip
                continue

            cache_key = (sg, future)
            twentyfour = twentyfour_cache.get(cache_key)
            if twentyfour is None:
                twentyfour, _ = FutureTrading24Hour.objects.get_or_create(
                    session_group=sg,
                    future=future,
                    defaults={
                        "session_date": row.timestamp_minute.date(),
                        "country": country,
                    },
                )
                twentyfour_cache[cache_key] = twentyfour

            row.twentyfour = twentyfour
            buffer.append(row)

            if len(buffer) >= batch_size:
                self._flush_buffer(buffer)
                linked += len(buffer)
                buffer.clear()

        if buffer:
            self._flush_buffer(buffer)
            linked += len(buffer)

        self.stdout.write(self.style.SUCCESS(f"Processed={processed} linked={linked} pending={max(processed - linked, 0)}"))

    def _flush_buffer(self, rows):
        if not rows:
            return
        with transaction.atomic():
            MarketIntraday.objects.bulk_update(rows, ["twentyfour"])
