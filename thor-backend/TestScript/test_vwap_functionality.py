#!/usr/bin/env python
"""Test VwapMinute model is accessible and functional."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from ThorTrading.models.vwap import VwapMinute
from django.utils import timezone

print("✅ VwapMinute model imported successfully")

# Check if we can query the table
count = VwapMinute.objects.count()
print(f"✅ VwapMinute table is queryable: {count} rows exist")

# Check if we can create a test row
test_symbol = "TEST_VWAP"
test_time = timezone.now().replace(second=0, microsecond=0)

# Clean up any existing test data
VwapMinute.objects.filter(symbol=test_symbol).delete()

# Try creating a row
obj, created = VwapMinute.objects.get_or_create(
    symbol=test_symbol,
    timestamp_minute=test_time,
    defaults={
        'last_price': 100.50,
        'bid_price': 100.45,
        'ask_price': 100.55,
        'cumulative_volume': 1000,
    }
)

if created:
    print(f"✅ Successfully created test row: {obj}")
else:
    print(f"✅ Test row already exists: {obj}")

# Clean up
VwapMinute.objects.filter(symbol=test_symbol).delete()
print("✅ Successfully deleted test row")

print("\n" + "=" * 60)
print("✅ VwapMinute model is FULLY FUNCTIONAL")
print("=" * 60)

