from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0027_marketsession_drop_sum_weighted_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="reference_open",
            new_name="session_open",
        ),
    ]
