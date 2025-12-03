from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0054_remove_change_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="marketsession",
            name="market_close_number",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_close_percentage",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_high_number",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_high_percentage",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_low_number",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_low_percentage",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_open",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_range_number",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="marketsession",
            name="market_range_percentage",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
    ]
