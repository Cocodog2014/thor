# Generated migration to simplify GlobalMarkets for US trading

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('GlobalMarkets', '0001_initial'),
    ]

    operations = [
        # Add open_time and close_time directly to Market
        migrations.AddField(
            model_name='market',
            name='open_time',
            field=models.TimeField(null=True, blank=True, help_text='Default market open time (local timezone)'),
        ),
        migrations.AddField(
            model_name='market',
            name='close_time',
            field=models.TimeField(null=True, blank=True, help_text='Default market close time (local timezone)'),
        ),
        
        # Make MarketHoliday apply to all markets (remove market FK)
        migrations.RemoveField(
            model_name='marketholiday',
            name='market',
        ),
        migrations.AddConstraint(
            model_name='marketholiday',
            constraint=models.UniqueConstraint(fields=('date',), name='uniq_holiday_date'),
        ),
        migrations.AlterModelOptions(
            name='marketholiday',
            options={'ordering': ['-date'], 'verbose_name': 'US Market Holiday', 'verbose_name_plural': 'US Market Holidays'},
        ),
    ]
