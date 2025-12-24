from django.db import migrations


def remove_futures_market(apps, schema_editor):
    Market = apps.get_model("GlobalMarkets", "Market")
    MarketDataSnapshot = apps.get_model("GlobalMarkets", "MarketDataSnapshot")

    futures_markets = list(Market.objects.filter(country__iexact="Futures"))
    if not futures_markets:
        return

    MarketDataSnapshot.objects.filter(market__in=futures_markets).delete()
    Market.objects.filter(pk__in=[m.pk for m in futures_markets]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("GlobalMarkets", "0015_merge_trading_days"),
    ]

    operations = [
        migrations.RunPython(remove_futures_market, migrations.RunPython.noop),
    ]
