#!/usr/bin/env python
"""Check what's actually in Redis right now."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from LiveData.shared.redis_client import live_data_redis

# Get YM quote from Redis
ym_quote = live_data_redis.get_latest_quote('YM')

if ym_quote:
    print("YM Quote in Redis:")
    for key, value in sorted(ym_quote.items()):
        print(f"  {key}: {value}")
else:
    print("No YM quote in Redis!")

print("\n" + "="*60 + "\n")

# Get all 11 futures
symbols = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
print("All futures in Redis:")
for symbol in symbols:
    quote = live_data_redis.get_latest_quote(symbol)
    if quote:
        last = quote.get('last', 'N/A')
        weight = quote.get('weight', 'N/A')
        signal = quote.get('signal', 'N/A')
        print(f"  {symbol}: last={last}, weight={weight}, signal={signal}")
    else:
        print(f"  {symbol}: NOT IN REDIS")
