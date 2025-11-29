# How to View Schwab Account Data in Terminal

## Method 1: Django Shell (Interactive - Best Option)

### Quick Check
```bash
cd A:\Thor\thor-backend
python manage.py shell < ../check_schwab.py
```

### Interactive Shell
```bash
cd A:\Thor\thor-backend
python manage.py shell
```

Then paste these commands:

```python
# Import what you need
from account_statement.models import RealAccount, BrokerageProvider
from django.contrib.auth import get_user_model

User = get_user_model()

# Get your user
user = User.objects.first()  # or User.objects.get(username='your_username')

# Check if Schwab is connected
if hasattr(user, 'schwab_token'):
    print("✅ Schwab connected")
    print(f"Token expired: {user.schwab_token.is_expired}")
else:
    print("❌ Need to connect Schwab")

# View Schwab accounts
accounts = RealAccount.objects.filter(
    brokerage_provider=BrokerageProvider.SCHWAB,
    user=user
)

for acc in accounts:
    print(f"\nAccount: {acc.account_number}")
    print(f"  Net Value: ${acc.net_liquidating_value:,.2f}")
    print(f"  Buying Power: ${acc.stock_buying_power:,.2f}")
    print(f"  Available: ${acc.available_funds_for_trading:,.2f}")
    print(f"  Last Sync: {acc.last_sync_date}")

# Fetch fresh data from Schwab API
from LiveData.schwab.services import SchwabTraderAPI

api = SchwabTraderAPI(user)
accounts_list = api.fetch_accounts()
print(f"Schwab has {len(accounts_list)} account(s)")

# Get summary
account_hash = accounts_list[0]['hashValue']
summary = api.get_account_summary(account_hash)
print(summary)
```

## Method 2: Django Admin (Web Interface)

1. Start server:
   ```bash
   cd A:\Thor\thor-backend
   python manage.py runserver
   ```

2. Visit: http://localhost:8000/admin/

3. Navigate to:
   - **Account Statement → Real Accounts** (to see synced data)
   - **Schwab → Schwab Tokens** (to see OAuth status)

## Method 3: Direct API Call

```bash
# Test the endpoint
curl http://localhost:8000/account_statement/real/schwab/summary/

# Pretty print
curl -s http://localhost:8000/account_statement/real/schwab/summary/ | python -m json.tool
```

## Method 4: Python Test Script

```bash
python test_schwab_account.py
```

## Method 5: Database Direct (PostgreSQL)

```bash
# Connect to database
psql -U thor_user -d thor_db

# Query accounts
SELECT account_number, 
       net_liquidating_value, 
       stock_buying_power,
       last_sync_date,
       brokerage_provider
FROM account_statement_realaccount
WHERE brokerage_provider = 'SCHWAB';

# Check OAuth tokens
SELECT user_id, 
       access_expires_at,
       created_at
FROM schwab_token;
```

## Quick Reference: Shell Commands

### Check Connection Status
```python
user = User.objects.first()
user.schwab_token.is_expired  # True/False
```

### Get Latest Account Data
```python
acc = RealAccount.objects.filter(brokerage_provider='SCHWAB').first()
acc.net_liquidating_value  # Decimal value
acc.last_sync_date  # When it was last updated
```

### Force Refresh from Schwab
```python
from LiveData.schwab.services import SchwabTraderAPI
api = SchwabTraderAPI(user)
summary = api.get_account_summary('account_hash_here')
```

### Update Account in Database
```python
acc = RealAccount.objects.filter(brokerage_provider='SCHWAB').first()
acc.stock_buying_power = 10000.00
acc.save()
```

## Troubleshooting

### "No Schwab account connected"
```python
# Check if token exists
User.objects.first().schwab_token
# If error, run OAuth first
```

### "Token expired"
```python
token = User.objects.first().schwab_token
import time
print(f"Expires at: {token.access_expires_at}")
print(f"Current time: {time.time()}")
print(f"Expired: {token.is_expired}")
# Need to re-run OAuth if expired
```

### See Raw Schwab Response
```python
from LiveData.schwab.services import SchwabTraderAPI
api = SchwabTraderAPI(user)
accounts = api.fetch_accounts()
print(accounts)  # Raw JSON from Schwab
```

## Best Practice Workflow

1. **First Time Setup:**
   ```bash
   # Complete OAuth
   # Visit: http://localhost:8000/api/schwab/oauth/start/
   
   # Check connection
   cd thor-backend
   python manage.py shell < ../check_schwab.py
   ```

2. **Daily Use:**
   ```bash
   # Quick check
   python manage.py shell
   >>> exec(open('../check_schwab.py').read())
   
   # Or use Django admin
   # http://localhost:8000/admin/
   ```

3. **Development:**
   ```bash
   # Interactive shell for testing
   python manage.py shell
   >>> from account_statement.models import RealAccount
   >>> acc = RealAccount.objects.first()
   >>> acc.net_liquidating_value
   ```

## Files Created for Terminal Viewing

- ✅ `check_schwab.py` - Quick status check
- ✅ `django_shell_commands.py` - Detailed exploration
- ✅ `test_schwab_account.py` - API endpoint test

Choose the method that works best for your workflow!
