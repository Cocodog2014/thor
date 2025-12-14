# Schwab Account Summary - Implementation Summary

## What We Built

Real-time Schwab account summary integration for the Account Statement app.

## Components Created

### 1. Schwab API Client (`LiveData/schwab/services.py`)
- `SchwabTraderAPI` class
- Methods:
  - `fetch_accounts()` - Get list of Schwab accounts
  - `fetch_account_details()` - Get detailed account data
  - `get_account_summary()` - Get formatted account summary
  
### 2. Account Statement Integration (`account_statement/views/real.py`)
- New function: `schwab_account_summary(request)`
- Fetches data from Schwab API
- Creates/updates `RealAccount` model with live data
- Auto-syncs balance fields
- Returns formatted JSON response

### 3. URL Routing
- **Account Statement Endpoint**: `/account_statement/real/schwab/summary/`
  - Persists data to database (RealAccount model)
  - Recommended for production use
  
- **Raw Schwab Endpoint**: `/api/schwab/account/summary/`
  - Direct API data without persistence
  - Useful for testing/debugging

## How It Works

### Flow Diagram
```
User Request
    ↓
/account_statement/real/schwab/summary/
    ↓
Check Schwab OAuth Token
    ↓
Call SchwabTraderAPI.get_account_summary()
    ↓
Fetch data from Schwab API
    ↓
Parse and format response
    ↓
Create/Update RealAccount in database
    ↓
Update balance fields:
  - net_liquidating_value
  - stock_buying_power
  - option_buying_power
  - available_funds_for_trading
  - long_stock_value
  - maintenance_requirement
  - margin_balance
    ↓
Return JSON response
```

### Database Integration

The endpoint automatically:
1. Creates a new `RealAccount` if it doesn't exist
2. Updates existing account if found
3. Sets `brokerage_provider` to SCHWAB
4. Marks account as verified and API-enabled
5. Updates `last_sync_date` timestamp
6. Parses currency strings and stores as Decimal

### Fields Synced

| Schwab API Field | RealAccount Model Field |
|-----------------|------------------------|
| net_liquidating_value | net_liquidating_value |
| stock_buying_power | stock_buying_power |
| option_buying_power | option_buying_power |
| available_funds_for_trading | available_funds_for_trading |
| long_stock_value | long_stock_value |
| cash_balance | current_balance |
| maintenance_requirement | maintenance_requirement |
| margin_balance | margin_balance |

## Testing

### 1. Complete OAuth (One Time)
```bash
# Visit this URL in browser
http://localhost:8000/api/schwab/oauth/start/
```

### 2. Test Account Summary
```bash
# Run the test script
python test_schwab_account.py

# Or curl
curl http://localhost:8000/account_statement/real/schwab/summary/
```

### 3. Check Database
```bash
# Django shell
python manage.py shell

>>> from account_statement.models import RealAccount
>>> acc = RealAccount.objects.filter(brokerage_provider='SCHWAB').first()
>>> print(f"Balance: ${acc.net_liquidating_value}")
>>> print(f"Last Sync: {acc.last_sync_date}")
```

## Error Handling

| Error Code | Meaning | Solution |
|-----------|---------|----------|
| 404 | No Schwab account connected | Complete OAuth at `/api/schwab/oauth/start/` |
| 401 | Not authenticated | Login to Django admin first |
| 500 | API error | Check Schwab API status, token expiration |

## Next Steps

1. ✅ Backend integration complete
2. ⬜ Add frontend component to display account summary
3. ⬜ Add automatic refresh/polling
4. ⬜ Implement token auto-refresh
5. ⬜ Add positions data sync
6. ⬜ Add order placement endpoints

## File Locations

```
thor-backend/
├── LiveData/schwab/
│   ├── services.py          # Schwab API client
│   ├── views.py             # OAuth and raw API views
│   └── urls.py              # /api/schwab/* routes
├── account_statement/
│   ├── views/real.py        # schwab_account_summary()
│   └── urls/real.py         # /account_statement/real/* routes
└── test_schwab_account.py   # Test script

Documentation:
├── SCHWAB_ACCOUNT_SUMMARY.md
└── SCHWAB_LIVE_DATA.md
```

## Configuration Required

### .env
```bash
SCHWAB_CLIENT_ID=your_client_id_here
SCHWAB_CLIENT_SECRET=your_secret_here
SCHWAB_ENV=production
SCHWAB_REDIRECT_URI=https://dev-thor.360edu.org/schwab/callback
SCHWAB_REDIRECT_URI_DEV=https://dev-thor.360edu.org/schwab/callback
```

### Schwab Developer Portal
- Callback URL must match `SCHWAB_REDIRECT_URI` (and `SCHWAB_REDIRECT_URI_DEV`, which we keep identical)
- Scopes: Read account data and positions

## Key Features

✅ Real-time account balances from Schwab  
✅ Automatic database sync  
✅ OAuth 2.0 authentication  
✅ Error handling and logging  
✅ Currency parsing (handles $86,219.32 format)  
✅ Account creation and updates  
✅ Timestamp tracking  
✅ Multiple account support  

## Support

For issues:
1. Check Django logs for errors
2. Verify OAuth token is valid
3. Test raw Schwab endpoint first
4. Check `last_sync_date` and `sync_errors` fields
