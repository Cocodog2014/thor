# Remove MarketSession - redundant now that Market has open_time/close_time

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('GlobalMarkets', '0002_simplify_for_us_trading'),
    ]

    operations = [
        # Drop the entire MarketSession table
        migrations.DeleteModel(
            name='MarketSession',
        ),
    ]
