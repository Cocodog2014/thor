from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0026_delete_marketintraday"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="InstrumentIntraday"),
                migrations.DeleteModel(name="Rolling52WeekStats"),
            ],
            database_operations=[],
        ),
    ]
