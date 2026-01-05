from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0030_remove_marketsession_vwap"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="ContractWeight"),
                migrations.DeleteModel(name="SignalStatValue"),
                migrations.DeleteModel(name="SignalWeight"),
                migrations.DeleteModel(name="TradingInstrument"),
                migrations.DeleteModel(name="InstrumentCategory"),
            ],
            database_operations=[],
        ),
    ]
