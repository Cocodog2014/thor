#!/usr/bin/env python
"""Quick script to check today's MarketSession records in the database."""
import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from collections import defaultdict
from FutureTrading.models.MarketSession import MarketSession
from django.utils import timezone

today = timezone.now()
print(f"Today: {today.year}/{today.month}/{today.day}")
print(f"Current time: {today.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print("-" * 60)

qs = (MarketSession.objects
       .filter(year=today.year, month=today.month, date=today.day)
       .order_by('country', 'session_number', 'future'))

groups = defaultdict(list)
for row in qs:
    key = (row.country, row.session_number)
    groups[key].append(row)

print(f"Total session groups today: {len(groups)}")
print()

if groups:
    for (country, session_number), rows in groups.items():
        rows_sorted = sorted(rows, key=lambda r: (r.future or ''))
        total_row = next((r for r in rows_sorted if (r.future or '').upper() == 'TOTAL'), None)
        session_signal = (total_row.bhs if total_row and total_row.bhs else rows_sorted[0].bhs)
        captured_at = max(r.captured_at for r in rows_sorted)
        print(f"  - {country}: Session #{session_number}")
        print(f"    Captured: {captured_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"    Signal (bhs): {session_signal}")
        print(f"    Rows captured: {len(rows_sorted)} futures")
        if total_row:
            print(f"    TOTAL weighted_avg={total_row.weighted_average} weight={total_row.weight}")
        print()
else:
    print("❌ No sessions captured today!")
    print()
    print("Recent captures:")
    recent = (MarketSession.objects
              .order_by('-captured_at')
              [:5])
    for row in recent:
        print(f"  - {row.country} #{row.session_number} {row.future}: {row.captured_at.strftime('%Y-%m-%d %H:%M:%S')} bhs={row.bhs}")
