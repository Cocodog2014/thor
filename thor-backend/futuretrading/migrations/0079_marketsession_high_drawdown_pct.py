from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0078_marketsession_bulk_field_renames"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="market_high_pct_open",
            new_name="market_high_drawdown_pct",
        ),
    ]
