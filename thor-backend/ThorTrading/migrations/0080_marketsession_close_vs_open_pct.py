from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0079_marketsession_high_drawdown_pct"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="market_close_vs_open_percentage",
            new_name="market_close_vs_open_pct",
        ),
    ]
