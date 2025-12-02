from decimal import Decimal

from django.db import migrations


OFFSET_CONFIG = {
    "ES": Decimal("2.00"),
    "NQ": Decimal("5.00"),
    "YM": Decimal("20.00"),
    "RTY": Decimal("2.00"),
    "CL": Decimal("0.10"),
    "GC": Decimal("1.00"),
    "SI": Decimal("0.02"),
    "HG": Decimal("0.004"),
    "VX": Decimal("0.10"),
    "DX": Decimal("2.00"),
    "ZB": Decimal("0.0938"),
}


def apply_target_offsets(apps, schema_editor):
    TargetHighLowConfig = apps.get_model("FutureTrading", "TargetHighLowConfig")

    for symbol, offset in OFFSET_CONFIG.items():
        TargetHighLowConfig.objects.update_or_create(
            symbol=symbol,
            defaults={
                "mode": "POINTS",
                "offset_high": offset,
                "offset_low": offset,
                "percent_high": None,
                "percent_low": None,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0047_set_contract_sizes"),
    ]

    operations = [
        migrations.RunPython(apply_target_offsets, migrations.RunPython.noop),
    ]
