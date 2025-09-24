# Schwab Live Data Provider System

## 🎯 Overview

The **SchwabLiveData** app provides a flexible provider system for market data that allows easy switching between fake/mock data (for development) and real Schwab API data (for production).

### Key Benefits
- **Development**: Use JSON file with realistic fake data
- **Production**: Switch to real Schwab API with one environment variable
- **No Code Changes**: Frontend and business logic remain unchanged when switching
- **Easy Testing**: Built-in simulation and health checks

---

## 🏗️ Architecture

```
Frontend (React)
       ↓
Django API Endpoint (/api/schwab/quotes/latest/)
       ↓
Provider Factory (selects provider)
       ↓
┌─────────────────┬─────────────────┐
│   JSON Provider │  Schwab Provider │
│   (Development) │   (Production)   │
└─────────────────┴─────────────────┘
       ↓                    ↓
  JSON File            Schwab API
```

---

## 📁 File Structure

```
thor-backend/
├── SchwabLiveData/               # New Django app
│   ├── futures_data.json         # 🗃️ FAKE DATA (delete when Schwab ready)
│   ├── providers.py              # Provider classes (JSON & Schwab)
│   ├── provider_factory.py       # Provider selection logic
│   ├── views.py                  # API endpoints
│   ├── urls.py                   # URL routing
│   └── management/commands/
│       └── test_provider.py      # Testing command
└── thor_project/
    ├── settings.py               # Added SchwabLiveData to INSTALLED_APPS
    └── urls.py                   # Added /api/schwab/ routes
```

---

## 🚀 Quick Start

### 1. Test the System
```bash
# Navigate to backend
cd thor-backend
.\venv\Scripts\Activate.ps1

# Test the provider system
python manage.py test_provider

# Start Django server
python manage.py runserver
```

### 2. Access API Endpoints
- **Market Data**: http://127.0.0.1:8000/api/schwab/quotes/latest/
- **Provider Status**: http://127.0.0.1:8000/api/schwab/provider/status/
- **Health Check**: http://127.0.0.1:8000/api/schwab/provider/health/

### 3. Frontend Integration
The frontend automatically tries the new provider first, then falls back to the old system:
```typescript
// Updated in FutureTrading.tsx
async function fetchQuotes(){
  const endpoints = [
    `/api/schwab/quotes/latest?ts=${Date.now()}`,  // New provider
    `/api/quotes/latest?ts=${Date.now()}`          // Fallback
  ];
  // Tries endpoints in order...
}
```

---

## 📊 Working with Fake Data (JSON Provider)

### Current JSON File Location
```
thor-backend/SchwabLiveData/futures_data.json
```

### JSON Structure
```json
{
  "futures": [
    {
      "symbol": "/YM",
      "name": "Dow Jones Mini Futures",
      "base_price": 317.92,
      "signal": "BUY",
      "stat_value": 10.000,
      "contract_weight": 1.5
    }
    // ... 10 more futures
  ]
}
```

### Modifying Fake Data

#### Option 1: Edit JSON File Directly
```bash
# Edit the JSON file
code thor-backend/SchwabLiveData/futures_data.json

# Changes take effect immediately (no restart needed)
```

#### Option 2: Replace Entire JSON File
```bash
# Backup current file
cp futures_data.json futures_data_backup.json

# Replace with your new data
# (just ensure it follows the same structure)
```

### Live Simulation Features

The JSON provider adds realistic behavior:
- **Price Movement**: Simulates realistic price changes from base prices
- **Signal Rotation**: Occasionally changes signals (BUY → SELL → HOLD)
- **Bid/Ask Spreads**: Realistic spreads per instrument type
- **Volume/Size**: Random but realistic trading volumes

**Control Simulation:**
```bash
# Disable live simulation (static prices)
export ENABLE_LIVE_SIMULATION=false

# Enable live simulation (default)
export ENABLE_LIVE_SIMULATION=true
```

---

## 🔄 Provider Switching

### Environment Variable Control
```bash
# Use JSON provider (default - for development)
export DATA_PROVIDER=json

# Use Schwab provider (for production)
export DATA_PROVIDER=schwab
```

### Testing Different Providers
```bash
# Test JSON provider
python manage.py test_provider --provider json

# Test Schwab provider (will show "not implemented" error)
python manage.py test_provider --provider schwab

# Test with no simulation
python manage.py test_provider --no-simulation
```

### Provider Priority
1. **Environment Variable**: `DATA_PROVIDER=json|schwab`
2. **Django Setting**: `DATA_PROVIDER` in settings.py
3. **Default**: `json` (safe fallback)

---

## 🌐 Switching to Real Schwab API

### Phase 1: Get Schwab API Access

1. **Apply for Schwab Developer Account**
   - Visit: https://developer.schwab.com/
   - Register for API access
   - Get your `client_id` and `client_secret`

2. **Understand Schwab API**
   - Read Schwab API documentation
   - Understand authentication (OAuth2)
   - Identify endpoints for futures data
   - Note field names and data formats

### Phase 2: Configure Environment

Set up environment variables for Schwab:
```bash
# Schwab API credentials
export SCHWAB_CLIENT_ID=your_client_id_here
export SCHWAB_CLIENT_SECRET=your_secret_here
export SCHWAB_BASE_URL=https://api.schwabapi.com
export SCHWAB_SCOPES=read

# Switch to Schwab provider
export DATA_PROVIDER=schwab
```

### Phase 3: Implement Schwab Provider

Edit `thor-backend/SchwabLiveData/providers.py`:

```python
class SchwabProvider(BaseProvider):
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        IMPLEMENT THIS METHOD when you have Schwab API access
        """
        # 1. Authenticate with Schwab (OAuth2)
        token = self._get_auth_token()
        
        # 2. Make API calls to get quotes
        schwab_data = self._fetch_schwab_quotes(symbols, token)
        
        # 3. Map Schwab fields to our standard format
        standardized_quotes = self._map_schwab_to_standard(schwab_data)
        
        return standardized_quotes
    
    def _get_auth_token(self):
        """Handle OAuth2 authentication with Schwab"""
        # TODO: Implement OAuth2 flow
        pass
    
    def _fetch_schwab_quotes(self, symbols, token):
        """Make REST API calls to Schwab"""
        # TODO: Implement API calls
        pass
    
    def _map_schwab_to_standard(self, schwab_data):
        """Convert Schwab response to our standard format"""
        # TODO: Map fields like:
        # schwab_response['last'] -> our_format['price']
        # schwab_response['bid'] -> our_format['bid']
        # etc.
        pass
```

### Phase 4: Test Schwab Integration

```bash
# Test Schwab connection
python manage.py test_provider --provider schwab

# Check health
curl http://127.0.0.1:8000/api/schwab/provider/health/

# Test API endpoint
curl http://127.0.0.1:8000/api/schwab/quotes/latest/
```

### Phase 5: Go Live

1. **Set Production Environment**:
   ```bash
   export DATA_PROVIDER=schwab
   export ENABLE_LIVE_SIMULATION=false
   ```

2. **Remove JSON File** (optional):
   ```bash
   rm thor-backend/SchwabLiveData/futures_data.json
   ```

3. **Deploy**: Your frontend continues working unchanged!

---

## 🛠️ Implementation Details

### Schwab API Integration Points

**Authentication (OAuth2)**:
```python
# You'll need to implement:
def authenticate_with_schwab():
    # 1. Get access token using client credentials
    # 2. Store token securely
    # 3. Handle token refresh
    pass
```

**Data Fetching**:
```python
# You'll need to implement:
def fetch_quotes_from_schwab(symbols):
    # 1. Make HTTP requests to Schwab endpoints
    # 2. Handle rate limits
    # 3. Parse responses
    # 4. Handle errors gracefully
    pass
```

**Field Mapping**:
```python
# Example mapping (actual fields may differ):
schwab_to_standard = {
    'last': 'price',
    'bidPrice': 'bid', 
    'askPrice': 'ask',
    'totalVolume': 'volume',
    # ... map all required fields
}
```

### Error Handling Strategy

```python
def get_latest_quotes(self, symbols):
    try:
        # Try Schwab API
        return self._fetch_from_schwab(symbols)
    except SchwabAPIError as e:
        # Log error, try fallback, or return cached data
        logger.error(f"Schwab API failed: {e}")
        return self._get_fallback_data(symbols)
```

---

## 🧪 Testing & Development

### Development Workflow

1. **Develop with JSON**: Start with fake data
2. **Test Provider Switching**: Verify environment variables work
3. **Implement Schwab**: Build real API integration
4. **Test Both**: Ensure both providers work
5. **Deploy**: Switch to Schwab in production

### Useful Commands

```bash
# Test current provider
python manage.py test_provider

# Test specific provider
python manage.py test_provider --provider json
python manage.py test_provider --provider schwab

# Test without simulation
python manage.py test_provider --no-simulation

# Get JSON output
python manage.py test_provider --format json

# Test specific symbols
python manage.py test_provider --symbols /YM /ES
```

### Monitoring

```bash
# Check provider status
curl http://127.0.0.1:8000/api/schwab/provider/status/

# Health check
curl http://127.0.0.1:8000/api/schwab/provider/health/

# Test endpoint
curl http://127.0.0.1:8000/api/schwab/quotes/latest/
```

---

## 🚨 Common Issues & Solutions

### Issue: "Provider not implemented"
**Solution**: You're trying to use Schwab provider before implementing it
```bash
export DATA_PROVIDER=json  # Switch back to JSON
```

### Issue: "JSON file not found"
**Solution**: Check file path and permissions
```bash
ls -la thor-backend/SchwabLiveData/futures_data.json
```

### Issue: Frontend not getting data
**Solution**: Check both endpoints are accessible
```bash
curl http://127.0.0.1:8000/api/schwab/quotes/latest/
curl http://127.0.0.1:8000/api/quotes/latest/
```

### Issue: Schwab API rate limits
**Solution**: Implement caching and retry logic
```python
# Add to SchwabProvider
def get_latest_quotes(self, symbols):
    # Check cache first
    cached = self._get_cached_data()
    if cached and not self._cache_expired():
        return cached
    
    # Fetch from API with rate limiting
    return self._fetch_with_rate_limit(symbols)
```

---

## 🎯 Summary

### Current State (JSON Provider)
- ✅ **11 futures** with exact data from your dashboard
- ✅ **Live simulation** with realistic price movements  
- ✅ **API endpoints** ready for frontend
- ✅ **Provider switching** via environment variables

### Future State (Schwab Provider)
- 🔄 **Same API endpoints** (no frontend changes)
- 🔄 **Same data format** (no business logic changes)
- ➕ **Real market data** from Schwab API
- ➕ **OAuth2 authentication** 
- ➕ **Production ready** with error handling

### The Transition
1. **Develop**: Use JSON provider with fake data
2. **Implement**: Build Schwab provider when API access available
3. **Switch**: Change one environment variable
4. **Delete**: Remove JSON file (optional)
5. **Done**: Real data flowing with zero code changes! 🎉

---

## 📞 Next Steps

1. **Test the current system** with your frontend
2. **Modify JSON data** as needed for your use cases
3. **Apply for Schwab API access** when ready
4. **Implement Schwab provider** following the templates above
5. **Switch over** with confidence knowing your frontend won't change!

The beauty of this system: **Your JSON file is temporary and will disappear in one step when Schwab is ready!** 🚀