from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0081_rename_market_high_drawdown_pct_marketsession_market_high_pct_open"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="vwap",
        ),
    ]
