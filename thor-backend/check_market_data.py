import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot
from datetime import datetime, timedelta

print('=== MARKET OPEN SESSIONS ===')
total_sessions = MarketOpenSession.objects.count()
print(f'Total sessions: {total_sessions}')

today = datetime.now()
today_sessions = MarketOpenSession.objects.filter(
    year=today.year, 
    month=today.month, 
    date=today.day
).count()
print(f'Sessions today: {today_sessions}')

last_24h = MarketOpenSession.objects.filter(
    captured_at__gte=datetime.now()-timedelta(hours=24)
).count()
print(f'Sessions last 24h: {last_24h}')

latest = MarketOpenSession.objects.order_by('-captured_at').first()
if latest:
    print(f'Latest session: {latest.captured_at} - {latest.country}')
    print(f'  Status: {latest.fw_nwdw}')
    print(f'  Market: {latest.market_name}')
else:
    print('Latest session: None')

print('\n=== FUTURE SNAPSHOTS ===')
total_snapshots = FutureSnapshot.objects.count()
print(f'Total snapshots: {total_snapshots}')

snapshots_24h = FutureSnapshot.objects.filter(
    session__captured_at__gte=datetime.now()-timedelta(hours=24)
).count()
print(f'Snapshots last 24h: {snapshots_24h}')

if total_snapshots > 0:
    sample = FutureSnapshot.objects.order_by('-id').first()
    print(f'\nSample latest snapshot:')
    print(f'  Symbol: {sample.symbol}')
    print(f'  Bid: {sample.bid_price}, Ask: {sample.ask_price}')
    print(f'  Last: {sample.last_price}')
    print(f'  Volume: {sample.volume}')
    print(f'  Open Interest: {sample.open_interest}')
    print(f'  Session: {sample.session.country} at {sample.session.captured_at}')
    
    # Check if we have recent data
    recent = FutureSnapshot.objects.filter(
        session__captured_at__gte=datetime.now()-timedelta(hours=12)
    ).order_by('-session__captured_at')[:5]
    
    if recent.exists():
        print(f'\n=== Recent Snapshots (last 12 hours) ===')
        for snap in recent:
            print(f'{snap.session.captured_at.strftime("%H:%M:%S")} - {snap.session.country} - {snap.symbol}: Bid={snap.bid_price} Ask={snap.ask_price} Vol={snap.volume}')
else:
    print('\nNo snapshots found in database!')

print('\n=== By Country ===')
countries = MarketOpenSession.objects.values_list('country', flat=True).distinct()
for country in countries:
    count = MarketOpenSession.objects.filter(country=country).count()
    print(f'{country}: {count} sessions')
