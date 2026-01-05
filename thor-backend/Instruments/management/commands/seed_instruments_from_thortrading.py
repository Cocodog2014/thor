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
    help = "DEPRECATED: TradingInstrument has been retired; no seeding is required."

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
        self.stdout.write(
            self.style.WARNING(
                "TradingInstrument has been retired; this command is now a no-op. "
                "Use the Instruments admin/API to manage the canonical instrument catalog."
            )
        )
