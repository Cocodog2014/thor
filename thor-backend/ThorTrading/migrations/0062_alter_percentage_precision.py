from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('FutureTrading', '0061_remove_vwap_bid_ask'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketsession',
            name='market_high_percentage',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='High move from open (percent)'),
        ),
        migrations.AlterField(
            model_name='marketsession',
            name='market_low_percentage',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='Low move from open (percent)'),
        ),
        migrations.AlterField(
            model_name='marketsession',
            name='market_close_percentage',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='Close move from open (percent)'),
        ),
        migrations.AlterField(
            model_name='marketsession',
            name='market_range_percentage',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='Intraday range (percent)'),
        ),
        migrations.AlterField(
            model_name='marketsession',
            name='range_percent',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='Range as % of previous close'),
        ),
        migrations.AlterField(
            model_name='marketsession',
            name='week_52_range_percent',
            field=models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text='52-week range as % of current price'),
        ),
    ]
