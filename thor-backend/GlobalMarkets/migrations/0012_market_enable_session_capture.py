from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GlobalMarkets", "0011_trading_calendar_exchange_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="market",
            name="enable_session_capture",
            field=models.BooleanField(default=True),
        ),
    ]
