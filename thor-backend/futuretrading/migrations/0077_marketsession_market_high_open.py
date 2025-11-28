from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0076_marketsession_high_pct_52w"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="market_high_number",
            new_name="market_high_open",
        ),
    ]
