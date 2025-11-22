from decimal import Decimal

from django.db import migrations


CONTRACT_SIZES = {
    "/ES": Decimal("50"),
    "/NQ": Decimal("20"),
    "/YM": Decimal("5"),
    "/RTY": Decimal("50"),
    "/CL": Decimal("1000"),
    "/GC": Decimal("100"),
    "/SI": Decimal("5000"),
    "/HG": Decimal("25000"),
    "/VX": Decimal("1000"),
    "/DX": Decimal("10"),
    "/ZB": Decimal("1000"),
}


def apply_contract_sizes(apps, schema_editor):
    TradingInstrument = apps.get_model("FutureTrading", "TradingInstrument")

    for symbol, contract_size in CONTRACT_SIZES.items():
        TradingInstrument.objects.filter(symbol=symbol).update(contract_size=contract_size)


class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0046_update_trading_instruments"),
    ]

    operations = [
        migrations.RunPython(apply_contract_sizes, migrations.RunPython.noop),
    ]
