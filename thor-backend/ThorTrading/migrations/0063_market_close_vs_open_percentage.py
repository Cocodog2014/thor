from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0062_alter_percentage_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="marketsession",
            name="market_close_vs_open_percentage",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Close vs open change (percent)",
                max_digits=14,
                null=True,
            ),
        ),
    ]
