from decimal import Decimal

from django.db import migrations


INSTRUMENT_SPECS = {
    "/ES": {
        "name": "E-mini S&P 500 Futures",
        "exchange": "CME",
        "display_precision": 2,
        "tick_size": Decimal("0.25"),
        "tick_value": Decimal("12.50"),
    },
    "/NQ": {
        "name": "E-mini Nasdaq 100 Futures",
        "exchange": "CME",
        "display_precision": 2,
        "tick_size": Decimal("0.25"),
        "tick_value": Decimal("5.00"),
    },
    "/YM": {
        "name": "E-mini Dow Futures",
        "exchange": "CBOT",
        "display_precision": 0,
        "tick_size": Decimal("1"),
        "tick_value": Decimal("5.00"),
    },
    "/RTY": {
        "name": "E-mini Russell 2000 Futures",
        "exchange": "CME",
        "display_precision": 1,
        "tick_size": Decimal("0.10"),
        "tick_value": Decimal("5.00"),
    },
    "/CL": {
        "name": "Crude Oil Futures",
        "exchange": "NYMEX",
        "display_precision": 2,
        "tick_size": Decimal("0.01"),
        "tick_value": Decimal("10.00"),
    },
    "/GC": {
        "name": "Gold Futures",
        "exchange": "COMEX",
        "display_precision": 1,
        "tick_size": Decimal("0.10"),
        "tick_value": Decimal("10.00"),
    },
    "/SI": {
        "name": "Silver Futures",
        "exchange": "COMEX",
        "display_precision": 3,
        "tick_size": Decimal("0.005"),
        "tick_value": Decimal("25.00"),
    },
    "/HG": {
        "name": "Copper Futures",
        "exchange": "COMEX",
        "display_precision": 4,
        "tick_size": Decimal("0.0005"),
        "tick_value": Decimal("12.50"),
    },
    "/VX": {
        "name": "VIX Futures",
        "exchange": "CFE",
        "display_precision": 2,
        "tick_size": Decimal("0.05"),
        "tick_value": Decimal("50.00"),
    },
    "/DX": {
        "name": "US Dollar Index Futures",
        "exchange": "ICE",
        "display_precision": 2,
        "tick_size": Decimal("0.01"),
        "tick_value": Decimal("0.10"),
    },
    "/ZB": {
        "name": "30-Year T-Bond Futures",
        "exchange": "CBOT",
        "display_precision": 3,
        "tick_size": Decimal("0.03125"),
        "tick_value": Decimal("31.25"),
    },
}


def upsert_instruments(apps, schema_editor):
    InstrumentCategory = apps.get_model("FutureTrading", "InstrumentCategory")
    TradingInstrument = apps.get_model("FutureTrading", "TradingInstrument")

    futures_category, _ = InstrumentCategory.objects.get_or_create(
        name="futures",
        defaults={
            "display_name": "Futures Contracts",
            "description": "CME, CBOT, NYMEX, COMEX futures",
            "is_active": True,
            "sort_order": 1,
        },
    )

    for symbol, spec in INSTRUMENT_SPECS.items():
        TradingInstrument.objects.update_or_create(
            symbol=symbol,
            defaults={
                "name": spec["name"],
                "category": futures_category,
                "exchange": spec["exchange"],
                "display_precision": spec["display_precision"],
                "tick_size": spec["tick_size"],
                "tick_value": spec["tick_value"],
                "is_active": True,
                "is_watchlist": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0045_fill_margin_requirement"),
    ]

    operations = [
        migrations.RunPython(upsert_instruments, migrations.RunPython.noop),
    ]
