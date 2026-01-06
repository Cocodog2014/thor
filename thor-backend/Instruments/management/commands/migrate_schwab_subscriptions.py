from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from Instruments.models import SchwabSubscription


@dataclass(frozen=True)
class _Row:
    user_id: int
    symbol: str
    asset_type: str
    enabled: bool


class Command(BaseCommand):
    help = "One-time copy of legacy LiveData schwab_subscription rows into Instruments-owned SchwabSubscription."  # noqa: E501

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=0,
            help="Optional: only migrate rows for this user_id",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing",
        )

    def handle(self, *args, **options):
        user_id = int(options.get("user_id") or 0)
        dry_run = bool(options.get("dry_run"))

        src_table = "schwab_subscription"  # legacy LiveData-owned table

        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            if src_table not in tables:
                self.stdout.write(self.style.WARNING(f"Source table not found: {src_table}"))
                return

            where = ""
            params: list[object] = []
            if user_id:
                where = " WHERE user_id = %s"
                params.append(user_id)

            cursor.execute(
                "SELECT user_id, symbol, asset_type, enabled FROM schwab_subscription" + where,
                params,
            )
            rows = [_Row(int(r[0]), str(r[1] or ""), str(r[2] or ""), bool(r[3])) for r in cursor.fetchall()]

        if not rows:
            self.stdout.write(self.style.SUCCESS("No legacy subscription rows found."))
            return

        self.stdout.write(f"Found {len(rows)} legacy row(s) in {src_table}.")

        created = 0
        updated = 0

        def _normalize_symbol(s: str) -> str:
            return (s or "").strip().upper()

        def _normalize_asset(s: str) -> str:
            return (s or "").strip().upper()

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no changes written."))

        with transaction.atomic():
            for r in rows:
                sym = _normalize_symbol(r.symbol)
                asset = _normalize_asset(r.asset_type) or SchwabSubscription.ASSET_EQUITY
                if not sym:
                    continue

                if dry_run:
                    continue

                obj, was_created = SchwabSubscription.objects.update_or_create(
                    user_id=r.user_id,
                    symbol=sym,
                    asset_type=asset,
                    defaults={"enabled": bool(r.enabled)},
                )
                if was_created:
                    created += 1
                else:
                    # update_or_create returns an updated object even if nothing changed
                    updated += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated legacy subscriptions → Instruments.SchwabSubscription. created={created} updated={updated}"
            )
        )
