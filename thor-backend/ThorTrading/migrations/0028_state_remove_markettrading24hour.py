from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0027_state_remove_intraday_and_52w"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="MarketTrading24Hour"),
            ],
            database_operations=[],
        ),
    ]
