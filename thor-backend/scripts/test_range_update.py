"""
Quick test to verify A1:N13 range returns correct symbols
"""
import requests
import json

resp = requests.get(
    'http://localhost:8000/api/feed/tos/quotes/latest/',
    params={'data_range': 'A1:N13'}
)

data = resp.json()
quotes = data.get('quotes', [])

print(f"Quotes count: {len(quotes)}\n")
print("All symbols:")
for i, q in enumerate(quotes, 1):
    symbol = q.get('symbol')
    last = q.get('last')
    print(f"  {i}. {symbol}: Last={last}")
