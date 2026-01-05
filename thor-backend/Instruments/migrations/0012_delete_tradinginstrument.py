from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0011_migrate_rtd_instrument_fks"),
    ]

    operations = [
        migrations.DeleteModel(name="TradingInstrument"),
    ]
