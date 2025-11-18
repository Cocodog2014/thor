#!/usr/bin/env python
"""Quick script to check today's MarketOpenSession records in the database."""
import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketSession import MarketOpenSession
from django.utils import timezone

today = timezone.now()
print(f"Today: {today.year}/{today.month}/{today.day}")
print(f"Current time: {today.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print("-" * 60)

sessions = MarketOpenSession.objects.filter(
    year=today.year, 
    month=today.month, 
    date=today.day
)

print(f"Total sessions today: {sessions.count()}")
print()

if sessions.count() > 0:
    for s in sessions:
        futures_count = s.futures.count()
        total_snapshot = s.futures.filter(symbol='TOTAL').first()
        print(f"  - {s.country}: Session #{s.session_number}")
        print(f"    Captured: {s.captured_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"    Signal: {s.total_signal}")
        print(f"    Futures: {futures_count} snapshots")
        if total_snapshot:
            print(f"    TOTAL: weighted_avg={total_snapshot.weighted_average}, signal={total_snapshot.signal}")
        print()
else:
    print("❌ No sessions captured today!")
    print()
    print("Recent sessions:")
    recent = MarketOpenSession.objects.all().order_by('-captured_at')[:5]
    for s in recent:
        print(f"  - {s.country}: {s.captured_at.strftime('%Y-%m-%d %H:%M:%S')}")
