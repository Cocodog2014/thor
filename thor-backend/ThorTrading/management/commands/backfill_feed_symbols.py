from __future__ import annotations

from django.core.management.base import BaseCommand

from ThorTrading.models.rtd import TradingInstrument


class Command(BaseCommand):
    help = "Backfill feed_symbol for instruments and normalize canonical symbol when safe."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report changes without writing them")
        parser.add_argument("--batch-size", type=int, default=1000, help="Rows to scan per chunk (default: 1000)")
        parser.add_argument("--verbose", action="store_true", help="Log progress per batch")

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)
        batch_size: int = options.get("batch_size", 1000)
        verbose: bool = options.get("verbose", False)

        updated_feed = 0
        updated_symbol = 0
        processed = 0

        qs = TradingInstrument.objects.all().order_by("pk")
        start = 0
        while True:
            batch = list(qs[start:start + batch_size])
            if not batch:
                break
            start += batch_size

            for inst in batch:
                processed += 1
                feed = inst.feed_symbol.strip() if inst.feed_symbol else ""
                if feed:
                    continue

                symbol = inst.symbol or ""
                if symbol.startswith("/"):
                    candidate_feed = symbol
                    candidate_symbol = symbol.lstrip("/") or symbol
                else:
                    continue

                can_update_symbol = False
                if candidate_symbol != symbol:
                    exists = (
                        TradingInstrument.objects
                        .filter(symbol=candidate_symbol)
                        .exclude(pk=inst.pk)
                        .exists()
                    )
                    can_update_symbol = not exists

                if not dry_run:
                    inst.feed_symbol = candidate_feed
                    fields = ["feed_symbol"]
                    if can_update_symbol:
                        inst.symbol = candidate_symbol
                        fields.append("symbol")
                        updated_symbol += 1
                    inst.save(update_fields=fields)
                else:
                    if can_update_symbol:
                        updated_symbol += 1
                updated_feed += 1

            if verbose:
                self.stdout.write(
                    f"Processed={processed} updated_feed={updated_feed} updated_symbol={updated_symbol}"
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run: feed_symbol to set={updated_feed}, symbols to normalize={updated_symbol}"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated feed_symbol on {updated_feed} instruments; normalized symbol on {updated_symbol} (where no conflicts)."
            )
        )
