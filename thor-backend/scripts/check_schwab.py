"""
Quick check script for Schwab account data.

Usage:
    cd thor-backend
    python manage.py shell < ../check_schwab.py
    
Or run interactively:
    python manage.py shell
    >>> exec(open('../check_schwab.py').read())
"""

from account_statement.models import RealAccount, BrokerageProvider
from LiveData.schwab.models import SchwabToken
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("SCHWAB ACCOUNT DATA CHECK")
print("=" * 60)

# Get first user (or modify to get specific user)
user = User.objects.first()

if not user:
    print("❌ No users found in database")
    exit()

print(f"\n👤 User: {user.username}")

# Check OAuth token
print("\n1️⃣  OAuth Status:")
if hasattr(user, 'schwab_token'):
    token = user.schwab_token
    print(f"   ✅ Schwab connected")
    print(f"   Token expires: {token.access_expires_at}")
    print(f"   Is expired: {token.is_expired}")
else:
    print("   ❌ No Schwab token")
    print("   → Run OAuth: http://localhost:8000/api/schwab/oauth/start/")

# Check accounts in database
print("\n2️⃣  Schwab Accounts in Database:")
schwab_accounts = RealAccount.objects.filter(
    brokerage_provider=BrokerageProvider.SCHWAB,
    user=user
)

if schwab_accounts.exists():
    for account in schwab_accounts:
        print(f"\n   📊 {account.account_number}")
        print(f"   └─ Net Value: ${account.net_liquidating_value:,.2f}")
        print(f"   └─ Buying Power: ${account.stock_buying_power:,.2f}")
        print(f"   └─ Last Sync: {account.last_sync_date}")
else:
    print("   ❌ No Schwab accounts found")
    print("   → Fetch data: http://localhost:8000/account_statement/real/schwab/summary/")

# Check all real accounts
print("\n3️⃣  All Real Accounts:")
all_accounts = RealAccount.objects.filter(user=user)
if all_accounts.exists():
    for acc in all_accounts:
        broker = acc.get_brokerage_provider_display()
        print(f"   • {acc.account_number} ({broker})")
else:
    print("   No real accounts found")

print("\n" + "=" * 60)
print("QUICK COMMANDS:")
print("=" * 60)
print("View account details:")
print("  >>> acc = RealAccount.objects.filter(brokerage_provider='SCHWAB').first()")
print("  >>> acc.net_liquidating_value")
print("\nFetch from Schwab API:")
print("  >>> from LiveData.schwab.services import SchwabTraderAPI")
print("  >>> api = SchwabTraderAPI(user)")
print("  >>> summary = api.get_account_summary('ACCOUNT_HASH')")
print("=" * 60)
