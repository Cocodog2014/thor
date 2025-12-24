from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GlobalMarkets", "0010_remove_market_is_control_market_remove_market_weight"),
    ]

    operations = [
        migrations.AddField(
            model_name="usmarketstatus",
            name="exchange_code",
            field=models.CharField(db_index=True, default="US", max_length=16),
        ),
        migrations.AlterField(
            model_name="usmarketstatus",
            name="date",
            field=models.DateField(),
        ),
        migrations.AddConstraint(
            model_name="usmarketstatus",
            constraint=models.UniqueConstraint(
                fields=["exchange_code", "date"], name="uniq_trading_calendar_day"
            ),
        ),
    ]
