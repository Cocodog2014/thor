"""Test the market opens API endpoint"""
import requests

url = "http://127.0.0.1:8000/api/market-opens/latest/"
print(f"Testing: {url}")

try:
    response = requests.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    if response.ok:
        data = response.json()
        print(f"Response type: {type(data)}")
        if isinstance(data, list):
            print(f"Sessions returned: {len(data)}")
            if data:
                print(f"First session country: {data[0].get('country')}")
                print(f"First session future: {data[0].get('future')}")
        else:
            print(f"Response: {data}")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Failed: {e}")
