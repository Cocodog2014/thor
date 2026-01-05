from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ThorTrading", "0028_state_remove_markettrading24hour"),
    ]

    operations = [
        migrations.DeleteModel(
            name="VwapMinute",
        ),
    ]
