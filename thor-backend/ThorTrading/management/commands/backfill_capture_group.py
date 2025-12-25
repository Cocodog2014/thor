from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import models, transaction

from ThorTrading.models.MarketSession import MarketSession


class Command(BaseCommand):
    help = "Backfill capture_group for MarketSession rows where it is NULL (set = session_number)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report counts without writing.")
        parser.add_argument("--batch-size", type=int, default=5000, help="Rows per batch update.")
        parser.add_argument("--verbose", action="store_true", help="Print progress per batch.")

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        batch_size: int = options["batch_size"]
        verbose: bool = options["verbose"]

        qs = MarketSession.objects.filter(capture_group__isnull=True)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No rows require backfill."))
            return

        null_session_number = qs.filter(session_number__isnull=True).count()
        self.stdout.write(f"Rows needing capture_group backfill: {total}")
        if null_session_number:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {null_session_number} rows have session_number=NULL; those will be skipped."
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no changes will be written."))
            return

        updated = 0
        skipped = 0

        while True:
            batch = list(
                MarketSession.objects.filter(capture_group__isnull=True)
                .values_list("pk", "session_number")[:batch_size]
            )
            if not batch:
                break

            ids_to_update = []
            for pk, session_number in batch:
                if session_number is None:
                    skipped += 1
                    continue
                ids_to_update.append(pk)

            with transaction.atomic():
                # Update only rows with usable session_number
                if ids_to_update:
                    updated_now = (
                        MarketSession.objects.filter(pk__in=ids_to_update, capture_group__isnull=True)
                        .update(capture_group=models.F("session_number"))
                    )
                    updated += updated_now

            if verbose:
                self.stdout.write(f"Batch processed={len(batch)} updated_total={updated} skipped_total={skipped}")

        remaining = MarketSession.objects.filter(capture_group__isnull=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. updated={updated} skipped={skipped} remaining_null={remaining}"
            )
        )

