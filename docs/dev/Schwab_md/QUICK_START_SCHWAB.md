# Quick Start Guide: Schwab Account Summary

## Setup (One Time)

### 1. Complete OAuth
Visit in your browser:
```
http://localhost:8000/api/schwab/oauth/start/
```
- Login to Schwab
- Authorize the application
- You'll be redirected back

### 2. Test the Integration
Run the test script:
```bash
python test_schwab_account.py
```

Or use curl:
```bash
curl http://localhost:8000/account_statement/real/schwab/summary/
```

## API Endpoint

### GET /account_statement/real/schwab/summary/

**Returns:**
```json
{
  "success": true,
  "created": false,
  "account_id": 1,
  "summary": {
    "net_liquidating_value": "$86,219.32",
    "stock_buying_power": "$295.38",
    "option_buying_power": "$300.00",
    "day_trading_buying_power": "$590.76",
    "available_funds_for_trading": "$301.95",
    "long_stock_value": "$85,917.37",
    "equity_percentage": "99.65%",
    "cash_balance": "$301.95",
    "maintenance_requirement": "$85,919.32",
    "margin_balance": "$0.00"
  },
  "account_info": {
    "account_number": "****1234",
    "last_sync": "2025-10-18T14:30:00Z"
  }
}
```

## What It Does

1. ✅ Fetches real-time data from Schwab API
2. ✅ Creates/updates RealAccount in database
3. ✅ Syncs all balance fields automatically
4. ✅ Returns formatted JSON for display

## Database

Check the synced account:
```python
from account_statement.models import RealAccount

# Get Schwab account
account = RealAccount.objects.filter(
    brokerage_provider='SCHWAB'
).first()

# View balances
print(f"Net Value: ${account.net_liquidating_value}")
print(f"Buying Power: ${account.stock_buying_power}")
print(f"Last Sync: {account.last_sync_date}")
```

## Troubleshooting

### "No Schwab account connected"
→ Complete OAuth first at `/api/schwab/oauth/start/`

### "Not authenticated"
→ Login to Django admin

### Account not creating
→ Check Django logs for errors
→ Verify SCHWAB_CLIENT_ID is set

## Files Modified

- ✅ `LiveData/schwab/services.py` - API client
- ✅ `account_statement/views/real.py` - View function
- ✅ `account_statement/urls/real.py` - URL routing

## Next Steps

Now you can:
1. View account in Django admin
2. Build frontend to display the summary
3. Add auto-refresh polling
4. Sync positions and orders
