from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0075_rename_week_52_range_high_low_marketsession_range_52w_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="high_pct_52",
            new_name="high_pct_52w",
        ),
    ]
