# Schwab Account Summary Integration

## Overview
Real-time account summary data from Charles Schwab's Trading API integrated into the Account Statement app.

## Setup Steps

### 1. Environment Variables
Ensure these are set in your `.env` file:
```bash
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_client_secret
SCHWAB_REDIRECT_URI=https://360edu.org/auth/callback
```

### 2. Complete OAuth Flow
1. Navigate to: `http://localhost:8000/api/schwab/oauth/start/`
2. Authorize the application in Schwab
3. You'll be redirected back and tokens will be saved

### 3. API Endpoints

#### Get Account Summary (Account Statement App)
```
GET /account_statement/real/schwab/summary/
```

**What It Does:**
- Fetches account summary from Schwab API
- Creates/updates RealAccount record in database
- Syncs all balance fields automatically
- Returns formatted summary for display

**Response:**
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

#### Direct Schwab API (Raw Data)
```
GET /api/schwab/account/summary/
```
Returns raw Schwab data without database persistence.

## Account Summary Fields

The endpoint returns the following fields matching the Stock Trading UI:

- **Net Liquidating Value**: Total account value
- **Stock Buying Power**: Available for stock purchases
- **Option Buying Power**: Available for option purchases  
- **Day Trading Buying Power**: For day trading (typically 4x)
- **Available Funds For Trading**: Cash available
- **Long Stock Value**: Current value of long positions
- **Equity Percentage**: Account equity as percentage

## Frontend Integration

### Example Usage
```typescript
const fetchAccountSummary = async () => {
  const response = await fetch('/api/schwab/account/summary/', {
    credentials: 'include'
  });
  const data = await response.json();
  return data.summary;
};
```

### Mode Toggle
The frontend should allow switching between:
- **Real Trading**: Uses Schwab API (this integration)
- **Paper Trading**: Uses paper trading account

## Testing

1. **Check OAuth Status**:
   ```bash
   curl http://localhost:8000/api/schwab/accounts/
   ```

2. **Get Account Summary**:
   ```bash
   curl http://localhost:8000/api/schwab/account/summary/
   ```

3. **Verify Response Format**:
   - All currency values formatted as "$X,XXX.XX"
   - Percentages formatted as "XX.XX%"
   - Account hash is included for subsequent calls

## Error Handling

- **404**: No Schwab account connected - need to complete OAuth
- **500**: API error - check token expiration or API issues
- **401**: Not authenticated - user needs to login

## Next Steps

1. ✅ Account summary endpoint created
2. ⬜ Frontend integration with Stock Trading page
3. ⬜ Add positions data
4. ⬜ Add order placement endpoints
5. ⬜ Implement token auto-refresh
