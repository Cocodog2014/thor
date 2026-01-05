from __future__ import annotations

from django.core.management.base import BaseCommand

from Instruments.models import Instrument


def _map_asset_type(category_name: str | None, symbol: str | None) -> str:
    name = (category_name or "").strip().lower()
    sym = (symbol or "").strip().upper()

    if sym.startswith("/"):
        return Instrument.AssetType.FUTURE

    if name in {"future", "futures", "futures contracts", "futures_contracts"}:
        return Instrument.AssetType.FUTURE

    if "crypto" in name:
        return Instrument.AssetType.CRYPTO
    if "forex" in name or "fx" == name:
        return Instrument.AssetType.FOREX
    if "index" in name:
        return Instrument.AssetType.INDEX
    if "etf" in name:
        return Instrument.AssetType.ETF

    return Instrument.AssetType.EQUITY


class Command(BaseCommand):
    help = "Seed Instruments.Instrument from existing ThorTrading.TradingInstrument rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would change without writing to DB.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            default=False,
            help="Include inactive TradingInstrument rows.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        include_inactive = bool(options.get("include_inactive"))

        from ThorTrading.studies.futures_total.models.rtd import TradingInstrument

        qs = TradingInstrument.objects.select_related("category")
        if not include_inactive:
            qs = qs.filter(is_active=True)

        created = 0
        updated = 0
        skipped = 0

        for ti in qs.order_by("country", "symbol"):
            symbol = (ti.symbol or "").strip().upper()
            if not symbol:
                skipped += 1
                continue

            asset_type = _map_asset_type(getattr(ti.category, "name", None), symbol)

            defaults = {
                "asset_type": asset_type,
                "name": (ti.name or "").strip()[:128],
                "exchange": (ti.exchange or "").strip()[:32],
                "currency": (ti.currency or "USD").strip()[:8],
                "country": (getattr(ti, "country", None) or "").strip()[:32],
                "sort_order": int(getattr(ti, "sort_order", 0) or 0),
                "display_precision": int(getattr(ti, "display_precision", 2) or 2),
                "margin_requirement": getattr(ti, "margin_requirement", None),
                "tick_size": getattr(ti, "tick_size", None),
                "point_value": getattr(ti, "contract_size", None),
                "is_active": bool(getattr(ti, "is_active", True)),
            }

            existing = Instrument.objects.filter(symbol=symbol).first()
            if existing is None:
                created += 1
                if not dry_run:
                    Instrument.objects.create(symbol=symbol, **defaults)
            else:
                # Update only missing/empty fields to avoid overwriting curated data.
                changed = False
                for field, value in defaults.items():
                    cur = getattr(existing, field)
                    if cur in (None, "") and value not in (None, ""):
                        setattr(existing, field, value)
                        changed = True
                # Always ensure asset_type is set
                if not existing.asset_type and defaults.get("asset_type"):
                    existing.asset_type = defaults["asset_type"]
                    changed = True

                if changed:
                    updated += 1
                    if not dry_run:
                        existing.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: created={created} updated={updated} skipped={skipped} dry_run={dry_run}"
            )
        )
