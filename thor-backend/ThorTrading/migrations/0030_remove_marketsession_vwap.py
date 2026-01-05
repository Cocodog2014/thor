from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ThorTrading", "0029_delete_vwapminute"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="vwap",
        ),
    ]
