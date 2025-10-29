#!/usr/bin/env python
"""Test the market-opens API endpoints."""
import requests

print("Testing /api/market-opens/latest/")
resp = requests.get('http://localhost:8000/api/market-opens/latest/')
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    print(f"Sessions returned: {len(data)}")
    for s in data[:3]:
        print(f"  - {s['country']}: captured_at={s['captured_at']}, signal={s.get('total_signal')}, futures={len(s.get('futures', []))}")
else:
    print(f"Error: {resp.text[:200]}")
