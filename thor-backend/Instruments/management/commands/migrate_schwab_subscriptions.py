from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from Instruments.models import Instrument, UserInstrumentWatchlistItem


@dataclass(frozen=True)
class _Row:
    user_id: int
    symbol: str
    asset_type: str
    enabled: bool


class Command(BaseCommand):
    help = "One-time migrate legacy LiveData schwab_subscription rows into the canonical user watchlist."  # noqa: E501

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
        created_instruments = 0
        created_watchlist = 0

        def _normalize_symbol(s: str) -> str:
            return (s or "").strip().upper()

        def _normalize_asset(s: str) -> str:
            return (s or "").strip().upper()

        def _to_instrument_symbol(sym: str, asset: str) -> str:
            # Futures are canonical with leading '/', equities without.
            if asset in {"FUTURE", "FUTURES"}:
                return sym if sym.startswith("/") else "/" + sym.lstrip("/")
            return sym.lstrip("/")

        def _to_instrument_asset_type(asset: str, sym: str) -> str:
            if asset in {"FUTURE", "FUTURES"} or sym.startswith("/"):
                return Instrument.AssetType.FUTURE
            return Instrument.AssetType.EQUITY

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no changes written."))

        # Deterministic ordering + per-user order field
        rows_sorted = sorted(rows, key=lambda rr: (rr.user_id, _normalize_asset(rr.asset_type), _normalize_symbol(rr.symbol)))

        with transaction.atomic():
            current_user_id: int | None = None
            order = 0

            for r in rows_sorted:
                sym = _normalize_symbol(r.symbol)
                asset = _normalize_asset(r.asset_type)
                if not sym:
                    continue

                if current_user_id != int(r.user_id):
                    current_user_id = int(r.user_id)
                    order = 0

                inst_symbol = _to_instrument_symbol(sym, asset)
                inst_asset_type = _to_instrument_asset_type(asset, sym)

                if dry_run:
                    order += 1
                    continue

                inst, inst_created = Instrument.objects.get_or_create(
                    symbol=inst_symbol,
                    defaults={"asset_type": inst_asset_type, "is_active": True},
                )
                if inst_created:
                    created_instruments += 1

                _, wl_created = UserInstrumentWatchlistItem.objects.get_or_create(
                    user_id=int(r.user_id),
                    instrument=inst,
                    defaults={
                        "enabled": bool(r.enabled),
                        "stream": bool(r.enabled),
                        "order": int(order),
                    },
                )
                if wl_created:
                    created_watchlist += 1

                order += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                "Migrated legacy subscriptions → Instruments.UserInstrumentWatchlistItem. "
                f"created_instruments={created_instruments} created_watchlist={created_watchlist}"
            )
        )
