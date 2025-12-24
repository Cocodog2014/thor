from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GlobalMarkets", "0013_remove_market_enable_futures_capture"),
    ]

    operations = [
        migrations.AddField(
            model_name="market",
            name="trading_days",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
