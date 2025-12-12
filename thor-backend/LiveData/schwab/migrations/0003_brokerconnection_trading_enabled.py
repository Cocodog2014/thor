from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("SchwabLiveData", "0002_broker_connections"),
    ]

    operations = [
        migrations.AddField(
            model_name="brokerconnection",
            name="trading_enabled",
            field=models.BooleanField(
                default=False,
                help_text="When true, Thor may send live orders for this connection.",
            ),
        ),
    ]
