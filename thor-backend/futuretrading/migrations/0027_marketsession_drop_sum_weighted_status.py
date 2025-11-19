from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "FutureTrading",
            "0026_marketsession_move_weight",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="sum_weighted",
        ),
        migrations.RemoveField(
            model_name="marketsession",
            name="status",
        ),
    ]
