#!/usr/bin/env python
"""Check the TOTAL snapshot data in detail."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot

# Get today's Japan session
session = MarketOpenSession.objects.filter(country='Japan').order_by('-captured_at').first()

if not session:
    print("No Japan session found!")
    exit(1)

print(f"Japan Session #{session.session_number}")
print(f"Captured: {session.captured_at}")
print(f"Signal: {session.total_signal}")
print(f"fw_weight: {session.fw_weight}")
print()

# Get the TOTAL snapshot
total = session.futures.filter(symbol='TOTAL').first()

if total:
    print("TOTAL Snapshot:")
    print(f"  weighted_average: {total.weighted_average}")
    print(f"  signal: {total.signal}")
    print(f"  weight: {total.weight}")
    print(f"  sum_weighted: {total.sum_weighted}")
    print(f"  instrument_count: {total.instrument_count}")
    print(f"  status: {total.status}")
    print()
else:
    print("❌ No TOTAL snapshot found!")
    print()

# Show all futures in this session
print(f"All futures in session ({session.futures.count()}):")
for f in session.futures.all():
    print(f"  {f.symbol}: signal={f.signal}, weight={f.weight}")
