# Generated data migration to set default feed values

from django.db import migrations


def set_default_feeds(apps, schema_editor):
    """Set default primary feeds for existing consumer apps."""
    ConsumerApp = apps.get_model("SchwabLiveData", "ConsumerApp")
    DataFeed = apps.get_model("SchwabLiveData", "DataFeed")
    
    # Get the Excel RTD feed as default primary
    try:
        excel_feed = DataFeed.objects.get(code="excel_rtd")
        schwab_feed = DataFeed.objects.get(code="schwab_api")
    except DataFeed.DoesNotExist:
        return  # Skip if feeds don't exist
    
    # Set defaults for existing consumer apps
    for consumer in ConsumerApp.objects.all():
        if not consumer.primary_feed:
            # Default mapping based on app type
            if consumer.code == "stock_trading":
                consumer.primary_feed = schwab_feed
                consumer.fallback_feed = excel_feed
            else:
                consumer.primary_feed = excel_feed
                consumer.fallback_feed = schwab_feed
            
            consumer.save()


def reverse_default_feeds(apps, schema_editor):
    """Reverse the default feed assignment."""
    # Nothing to reverse - the fields will be removed
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("SchwabLiveData", "0006_simplify_consumer_feeds"),
    ]

    operations = [
        migrations.RunPython(set_default_feeds, reverse_default_feeds),
    ]