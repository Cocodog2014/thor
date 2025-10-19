"""
Django Shell Commands - Schwab Account Summary

Run: python manage.py shell
Then paste these commands to explore your data.
"""

# Import models
from account_statement.models import RealAccount, BrokerageProvider
from LiveData.schwab.models import SchwabToken
from django.contrib.auth import get_user_model

User = get_user_model()

# ========================================
# 1. Check if Schwab OAuth is connected
# ========================================
user = User.objects.first()  # Or get your specific user
if hasattr(user, 'schwab_token'):
    token = user.schwab_token
    print(f"✅ Schwab connected for: {user.username}")
    print(f"   Token expires at: {token.access_expires_at}")
    print(f"   Is expired: {token.is_expired}")
else:
    print("❌ No Schwab token found. Run OAuth first.")

# ========================================
# 2. Check for Schwab accounts
# ========================================
schwab_accounts = RealAccount.objects.filter(
    brokerage_provider=BrokerageProvider.SCHWAB
)

print(f"\n📊 Found {schwab_accounts.count()} Schwab account(s)")

for account in schwab_accounts:
    print(f"\n--- Account: {account.account_number} ---")
    print(f"Nickname: {account.account_nickname}")
    print(f"Net Liquidating Value: ${account.net_liquidating_value:,.2f}")
    print(f"Stock Buying Power: ${account.stock_buying_power:,.2f}")
    print(f"Option Buying Power: ${account.option_buying_power:,.2f}")
    print(f"Available Funds: ${account.available_funds_for_trading:,.2f}")
    print(f"Long Stock Value: ${account.long_stock_value:,.2f}")
    print(f"Current Balance: ${account.current_balance:,.2f}")
    print(f"Last Sync: {account.last_sync_date}")
    print(f"Verified: {account.is_verified}")

# ========================================
# 3. Fetch fresh data from Schwab API
# ========================================
if hasattr(user, 'schwab_token'):
    from LiveData.schwab.services import SchwabTraderAPI
    
    try:
        api = SchwabTraderAPI(user)
        
        # List all accounts
        print("\n🔍 Fetching accounts from Schwab API...")
        accounts = api.fetch_accounts()
        print(f"Found {len(accounts)} account(s) at Schwab")
        
        # Get summary for first account
        if accounts:
            account_hash = accounts[0].get('hashValue')
            print(f"\n📈 Fetching summary for account: {account_hash[:8]}...")
            summary = api.get_account_summary(account_hash)
            
            print("\nSummary Data:")
            for key, value in summary.items():
                if key != 'positions':  # Skip positions list
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Error fetching from Schwab: {e}")

# ========================================
# 4. View all real accounts (any broker)
# ========================================
all_real_accounts = RealAccount.objects.all()
print(f"\n📋 Total Real Accounts: {all_real_accounts.count()}")
for acc in all_real_accounts:
    print(f"  - {acc.account_number} ({acc.get_brokerage_provider_display()})")
