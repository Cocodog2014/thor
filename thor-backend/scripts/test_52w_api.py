"""
Quick test script to verify 52w data flows through the API
"""
import requests
import json

try:
    response = requests.get('http://localhost:8000/api/quotes/latest', timeout=10)
    response.raise_for_status()
    
    data = response.json()
    print(f"✓ API returned {len(data['rows'])} rows\n")
    
    # Check a few symbols
    for symbol in ['YM', 'ES', 'NQ']:
        rows = [row for row in data['rows'] if row['instrument']['symbol'] == symbol]
        if rows:
            row = rows[0]
            ext = row.get('extended_data', {})
            print(f"{symbol}:")
            print(f"  Last: {row.get('price')}")
            print(f"  52w High: {ext.get('high_52w')}")
            print(f"  52w Low: {ext.get('low_52w')}")
            
            # Check if metrics were calculated
            if 'last_52w_above_low_diff' in row:
                print(f"  Distance from 52w Low: {row.get('last_52w_above_low_diff')}")
            if 'last_52w_below_high_diff' in row:
                print(f"  Distance from 52w High: {row.get('last_52w_below_high_diff')}")
            print()
        
except Exception as e:
    print(f"✗ Error: {e}")
