from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0003_alter_marketintraday_ask_last_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketintraday",
            name="market_code",
        ),
    ]
