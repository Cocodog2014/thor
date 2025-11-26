#!/usr/bin/env python
"""Quick VWAP calculation test harness.

Creates synthetic minute snapshots for a test symbol and verifies the
VWAP matches expected value.
"""
import os, sys
from decimal import Decimal
from django.utils import timezone

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
import django

django.setup()

from FutureTrading.models.vwap import VwapMinute
from FutureTrading.services.vwap import vwap_service

TEST_SYMBOL = 'TESTVWAP2'

# Clean existing test data
VwapMinute.objects.filter(symbol=TEST_SYMBOL).delete()

now = timezone.now().replace(second=0, microsecond=0)
minutes = [now, now + timezone.timedelta(minutes=1), now + timezone.timedelta(minutes=2)]
prices = [Decimal('10.0'), Decimal('10.5'), Decimal('11.0')]
# cumulative volumes (implies incremental: 100,150,150)
volumes = [100, 250, 400]

for ts, p, cv in zip(minutes, prices, volumes):
    VwapMinute.objects.create(symbol=TEST_SYMBOL, timestamp_minute=ts, last_price=p, cumulative_volume=cv)

# Expected VWAP: (10*100 + 10.5*150 + 11*150) / 400 = 4225 / 400 = 10.5625
expected = Decimal('10.5625')
result = vwap_service.calculate_vwap(TEST_SYMBOL, start=minutes[0], end=minutes[-1])
print(f"Numerator: {result.numerator}")
print(f"Denominator: {result.denominator}")
print(f"Computed VWAP: {result.vwap}")
print(f"Expected VWAP: {expected}")

if result.vwap == expected:
    print("SUCCESS: VWAP matches expected value")
else:
    print("FAIL: VWAP mismatch")

# Cleanup
VwapMinute.objects.filter(symbol=TEST_SYMBOL).delete()
