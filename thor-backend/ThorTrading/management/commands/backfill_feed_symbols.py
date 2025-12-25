from __future__ import annotations
from django.core.management.base import BaseCommand
from django.db import transaction

from ThorTrading.models.rtd import TradingInstrument


class Command(BaseCommand):
    help = "Backfill feed_symbol for instruments and normalize canonical symbol when safe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report changes without writing them",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        updated_feed = 0
        updated_symbol = 0

        with transaction.atomic():
            for inst in TradingInstrument.objects.all():
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
                    updated_symbol += 1 if can_update_symbol else 0
                updated_feed += 1

            if dry_run:
                raise SystemExit(self.style.WARNING(
                    f"Dry run: feed_symbol to set={updated_feed}, symbols to normalize={updated_symbol}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Updated feed_symbol on {updated_feed} instruments; normalized symbol on {updated_symbol} (where no conflicts)."
        ))
