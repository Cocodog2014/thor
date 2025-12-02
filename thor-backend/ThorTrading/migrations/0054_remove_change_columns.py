from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0053_move_spread_after_last_price"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="change",
        ),
        migrations.RemoveField(
            model_name="marketsession",
            name="change_percent",
        ),
    ]
