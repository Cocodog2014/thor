from decimal import Decimal

from django.db import migrations


MARGIN_PLACEHOLDER = Decimal("10000.00")


def apply_margin_placeholders(apps, schema_editor):
    TradingInstrument = apps.get_model("FutureTrading", "TradingInstrument")

    symbols = [
        "/ES",
        "/NQ",
        "/YM",
        "/RTY",
        "/CL",
        "/GC",
        "/SI",
        "/HG",
        "/VX",
        "/DX",
        "/ZB",
    ]

    for symbol in symbols:
        TradingInstrument.objects.filter(symbol=symbol, margin_requirement__isnull=True).update(
            margin_requirement=MARGIN_PLACEHOLDER
        )


def remove_margin_placeholders(apps, schema_editor):
    TradingInstrument = apps.get_model("FutureTrading", "TradingInstrument")

    TradingInstrument.objects.filter(margin_requirement=MARGIN_PLACEHOLDER).update(margin_requirement=None)


class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0044_add_wndw_back"),
    ]

    operations = [
        migrations.RunPython(apply_margin_placeholders, remove_margin_placeholders),
    ]
