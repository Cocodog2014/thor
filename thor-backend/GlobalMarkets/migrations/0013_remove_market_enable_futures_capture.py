from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("GlobalMarkets", "0012_market_enable_session_capture"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="market",
            name="enable_futures_capture",
        ),
    ]
