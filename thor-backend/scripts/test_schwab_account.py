"""
Test script for Schwab account summary integration.

Run this after completing OAuth to test the account summary endpoint.
"""

import requests

BASE_URL = "http://localhost:8000"

def test_account_statement_summary():
    """Test the account statement Schwab summary endpoint."""
    url = f"{BASE_URL}/account_statement/real/schwab/summary/"
    
    print("Testing Account Statement Schwab Summary Endpoint")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Success!")
            print()
            
            if data.get('created'):
                print("  ✨ New RealAccount created in database")
            else:
                print("  ♻️  Existing RealAccount updated")
            
            print()
            print("Account Summary:")
            print("-" * 60)
            
            if 'summary' in data:
                summary = data['summary']
                for key, value in summary.items():
                    print(f"  {key:.<40} {value}")
            
            print()
            if 'account_info' in data:
                info = data['account_info']
                print("Account Info:")
                print(f"  Account Number: {info.get('account_number')}")
                print(f"  Last Sync: {info.get('last_sync')}")
                print(f"  Account ID (DB): {data.get('account_id')}")
            
        elif response.status_code == 404:
            print("✗ No Schwab account connected")
            print("  Please complete OAuth flow first:")
            print(f"  {BASE_URL}/api/schwab/oauth/start/")
            
        elif response.status_code == 401:
            print("✗ Not authenticated")
            print("  Please login first")
            
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection Error")
        print("  Make sure Django server is running on port 8000")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def test_list_accounts():
    """Test listing all accounts."""
    url = f"{BASE_URL}/api/schwab/accounts/"
    
    print("\nTesting List Accounts Endpoint")
    print("=" * 50)
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Success!")
            print(f"  Found {len(data.get('accounts', []))} account(s)")
        else:
            print(f"✗ Error: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    test_account_statement_summary()
    test_list_accounts()
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("\nEndpoints Available:")
    print("  Account Statement: /account_statement/real/schwab/summary/")
    print("  Raw Schwab API:    /api/schwab/account/summary/")
    print("\nNext Steps:")
    print("1. If OAuth needed: Visit /api/schwab/oauth/start/")
    print("2. Check RealAccount in Django admin")
    print("3. Balances are auto-synced from Schwab API")
