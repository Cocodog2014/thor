from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0063_market_close_vs_open_percentage"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="market_close_percentage",
            new_name="market_close_percentage_high",
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_close_percentage_low",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Percent distance above intraday low",
                max_digits=14,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="marketsession",
            name="market_close_percentage_high",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Percent distance from intraday high",
                max_digits=14,
                null=True,
            ),
        ),
    ]
