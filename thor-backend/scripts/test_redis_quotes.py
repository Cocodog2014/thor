"""
Test script to check if 24h high/low data is in Redis
"""
import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from LiveData.shared.redis_client import live_data_redis
import json

# Test symbols
symbols = ['YM', 'ES', 'NQ']

print("=" * 60)
print("Checking Redis for 24h High/Low data")
print("=" * 60)

for symbol in symbols:
    print(f"\n{symbol}:")
    quote = live_data_redis.get_latest_quote(symbol)
    
    if quote:
        print(f"  ✓ Found data in Redis")
        print(f"  Last: {quote.get('last', 'N/A')}")
        print(f"  High (24h): {quote.get('high', 'N/A')}")
        print(f"  Low (24h): {quote.get('low', 'N/A')}")
        print(f"  High_52w: {quote.get('high_52w', 'N/A')}")
        print(f"  Low_52w: {quote.get('low_52w', 'N/A')}")
        print(f"  Available keys: {list(quote.keys())}")
    else:
        print(f"  ✗ No data found in Redis")

print("\n" + "=" * 60)
print("Now triggering Excel read to populate Redis...")
print("=" * 60)

# Trigger the TOS endpoint to read Excel and populate Redis
import requests
try:
    response = requests.get(
        'http://localhost:8000/api/feed/tos/quotes/latest/',
        params={'consumer': 'test_script'},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        quotes = data.get('quotes', [])
        print(f"\n✓ Successfully read {len(quotes)} quotes from Excel")
        
        # Check YM specifically
        ym_quotes = [q for q in quotes if q.get('symbol') == 'YM']
        if ym_quotes:
            ym = ym_quotes[0]
            print(f"\nYM data from Excel:")
            print(f"  Last: {ym.get('last', 'N/A')}")
            print(f"  High (24h): {ym.get('high', 'N/A')}")
            print(f"  Low (24h): {ym.get('low', 'N/A')}")
    else:
        print(f"✗ TOS endpoint returned status {response.status_code}")
        
except Exception as e:
    print(f"✗ Error calling TOS endpoint: {e}")

print("\n" + "=" * 60)
print("Checking Redis again after Excel read...")
print("=" * 60)

for symbol in symbols:
    print(f"\n{symbol}:")
    quote = live_data_redis.get_latest_quote(symbol)
    
    if quote:
        print(f"  ✓ Found data in Redis")
        print(f"  High (24h): {quote.get('high', 'N/A')}")
        print(f"  Low (24h): {quote.get('low', 'N/A')}")
    else:
        print(f"  ✗ Still no data in Redis")
