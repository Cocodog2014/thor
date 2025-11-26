#!/usr/bin/env python
"""Check the TOTAL snapshot data in detail."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketSession import MarketSession

# Get most recent Japan TOTAL row
total_row = (MarketSession.objects
             .filter(country='Japan', future='TOTAL')
             .order_by('-captured_at')
             .first())

if not total_row:
    print("No Japan TOTAL row found!")
    exit(1)

print(f"Japan Session #{total_row.session_number}")
print(f"Captured: {total_row.captured_at}")
print(f"Signal (bhs): {total_row.bhs}")
print(f"Weight: {total_row.weight}")
print(f"Weighted Avg: {total_row.weighted_average}")
print(f"Instrument Count: {total_row.instrument_count}")
print()

# Pull sibling futures for same capture
siblings = (MarketSession.objects
            .filter(
                country=total_row.country,
                session_number=total_row.session_number,
                year=total_row.year,
                month=total_row.month,
                date=total_row.date,
            )
            .exclude(future='TOTAL')
            .order_by('future'))

print(f"Futures captured for this session ({siblings.count()} rows):")
for row in siblings:
    print(f"  {row.future}: bhs={row.bhs} last={row.last_price} change={row.change} weight={row.weight}")
