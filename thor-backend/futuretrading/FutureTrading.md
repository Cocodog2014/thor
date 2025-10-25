# FutureTrading Module

## Overview

The **FutureTrading** module is a comprehensive Django application designed to provide real-time futures market data, advanced signal classification, and weighted composite scoring for trading instruments. It serves as the backend engine for the Thor platform's futures trading dashboard, delivering enriched market data with buy/sell signals, statistical values, and market sentiment analysis.

### Key Features

- **Real-time Market Data**: Integrates with TOS (ThinkOrSwim) Excel RTD to fetch live futures quotes
- **Signal Classification**: Automatically classifies market movements into actionable signals (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
- **Weighted Composite Scoring**: Calculates overall market sentiment using configurable instrument and signal weights
- **Flexible Instrument Management**: Supports multiple instrument types (futures, stocks, crypto, forex) with category-based organization
- **Bear Market Intelligence**: Special handling for inverse instruments (VX, DX, GC, ZB) that move opposite to equity markets
- **Statistical Value Mapping**: Configurable thresholds for signal classification per instrument
- **RESTful API**: Clean JSON endpoints for frontend consumption

---

## Architecture

### Module Structure

```
FutureTrading/
├── models.py                      # Database models
├── views.py                       # API endpoints
├── urls.py                        # URL routing
├── admin.py                       # Django admin configuration
├── apps.py                        # App configuration
├── config.py                      # Application settings
├── tests.py                       # Unit tests
├── services/
│   ├── classification.py          # Signal classification logic
│   └── metrics.py                 # Derived metrics computation
├── migrations/                    # Database migrations
└── static/                        # Static assets
```

---

## Data Models

### 1. InstrumentCategory

Organizes trading instruments into logical groups for UI presentation.

**Fields:**
- `name`: Unique identifier (e.g., 'futures', 'stocks', 'crypto', 'forex')
- `display_name`: Human-readable name (e.g., 'Futures Contracts', 'Stocks & ETFs')
- `description`: Detailed description of the category
- `is_active`: Enable/disable category
- `sort_order`: Display order in UI
- `color_primary`: Hex color for UI theming
- `color_secondary`: Secondary hex color
- `created_at`, `updated_at`: Timestamps

**Purpose:** Enables multi-asset class support while maintaining clean separation in the UI.

---

### 2. TradingInstrument

Core model representing any tradable instrument.

**Fields:**

**Basic Identification:**
- `symbol`: Unique trading symbol (e.g., '/NQ', 'AAPL', 'BTC-USD')
- `name`: Full name (e.g., 'Nasdaq 100 Futures', 'Apple Inc')
- `description`: Additional details

**Categorization:**
- `category`: ForeignKey to InstrumentCategory

**Market Information:**
- `exchange`: Trading venue (e.g., 'CME', 'NASDAQ', 'Binance')
- `currency`: Base currency (default: 'USD')

**Trading Configuration:**
- `is_active`: Enable/disable trading
- `is_watchlist`: Show in main watchlist
- `sort_order`: Display order

**Display Configuration:**
- `display_precision`: Decimal places for price display
- `tick_size`: Minimum price movement
- `contract_size`: Contract multiplier

**API Configuration:**
- `api_provider`: Data source identifier
- `api_symbol`: Provider-specific symbol
- `update_frequency`: Refresh interval in seconds

**Status:**
- `last_updated`: Last data refresh timestamp
- `is_market_open`: Current market status

**Purpose:** Flexible model supporting futures, stocks, crypto, forex, and other instruments with provider-agnostic design.

---

### 3. SignalStatValue

Maps signal classifications to numeric statistical values per instrument.

**Fields:**
- `instrument`: ForeignKey to TradingInstrument
- `signal`: Choice field (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
- `value`: Decimal value used for classification thresholds and weighted calculations
- `created_at`, `updated_at`: Timestamps

**Example:**
```
YM (Dow Jones):
- STRONG_BUY: 60.0
- BUY: 10.0
- HOLD: 0.0
- SELL: -10.0
- STRONG_SELL: -60.0

ES (S&P 500):
- STRONG_BUY: 6.0
- BUY: 1.0
- HOLD: 0.0
- SELL: -1.0
- STRONG_SELL: -6.0
```

**Purpose:** Provides configurable thresholds for signal classification based on each instrument's typical price movement characteristics.

---

### 4. SignalWeight

Global weights for signal types used in composite scoring.

**Fields:**
- `signal`: Choice field (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL) - unique
- `weight`: Integer weight value (e.g., 2, 1, 0, -1, -2)
- `created_at`, `updated_at`: Timestamps

**Standard Weights:**
- STRONG_BUY: +2
- BUY: +1
- HOLD: 0
- SELL: -1
- STRONG_SELL: -2

**Purpose:** Enables calculation of composite market sentiment by weighting individual instrument signals.

---

### 5. ContractWeight

Per-instrument weights for composite score calculation.

**Fields:**
- `instrument`: OneToOneField to TradingInstrument
- `weight`: Decimal weight (default: 1.0)
- `created_at`, `updated_at`: Timestamps

**Purpose:** Allows certain instruments to have more/less influence on the overall market composite score (e.g., ES might be weighted higher than VX).

---

## API Endpoints

### GET `/api/futuretrading/quotes/latest`

Returns enriched market data with signals and composite scoring.

**Response Structure:**
```json
{
  "rows": [
    {
      "instrument": {
        "id": 1,
        "symbol": "YM",
        "name": "Dow Jones E-mini",
        "exchange": "TOS",
        "currency": "USD",
        "display_precision": 2,
        "is_active": true,
        "sort_order": 0
      },
      "price": "43250.00",
      "last": "43250.00",
      "bid": "43249.00",
      "ask": "43251.00",
      "volume": 125000,
      "open_price": "43180.00",
      "high_price": "43280.00",
      "low_price": "43150.00",
      "close_price": "43200.00",
      "previous_close": "43200.00",
      "change": "50.00",
      "change_percent": "0.12",
      "bid_size": 10,
      "ask_size": 15,
      "market_status": "CLOSED",
      "data_source": "TOS_RTD",
      "is_real_time": true,
      "delay_minutes": 0,
      "timestamp": "2025-10-25T14:30:00Z",
      "extended_data": {
        "signal": "BUY",
        "stat_value": "10.0",
        "contract_weight": "1.0",
        "signal_weight": "1"
      },
      "last_prev_diff": 50.0,
      "last_prev_pct": 0.116,
      "open_prev_diff": -20.0,
      "open_prev_pct": -0.046,
      "high_prev_diff": 80.0,
      "high_prev_pct": 0.185,
      "low_prev_diff": -50.0,
      "low_prev_pct": -0.116,
      "range_diff": 130.0,
      "range_pct": 0.301,
      "spread": 2.0
    }
    // ... 10 more instruments
  ],
  "total": {
    "sum_weighted": "125.50",
    "avg_weighted": "11.409",
    "count": 11,
    "denominator": "11.00",
    "as_of": "2025-10-25T14:30:00Z",
    "signal_weight_sum": 5,
    "composite_signal": "BUY",
    "composite_signal_weight": 1
  }
}
```

**Key Fields Explained:**

- **rows**: Array of enriched market data per instrument
- **extended_data.signal**: Classification (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)
- **extended_data.stat_value**: Numeric value from SignalStatValue table
- **extended_data.contract_weight**: Per-instrument weighting
- **extended_data.signal_weight**: Global signal weight (2, 1, 0, -1, -2)
- **total.composite_signal**: Overall market sentiment
- **total.signal_weight_sum**: Sum of all signal weights

---

## Signal Classification Logic

### Classification Algorithm

The signal classification follows a threshold-based approach using the `SignalStatValue` table:

```python
Given net_change and instrument's SignalStatValue thresholds:

if net_change > STRONG_BUY_threshold:
    signal = "STRONG_BUY"
elif net_change > BUY_threshold:
    signal = "BUY"
elif net_change >= SELL_threshold:
    signal = "HOLD"
elif net_change > STRONG_SELL_threshold:
    signal = "SELL"
else:
    signal = "STRONG_SELL"
```

**Example:** For ES (S&P 500) with change = +3.5:
- STRONG_BUY: 6.0
- BUY: 1.0
- HOLD: 0.0
- SELL: -1.0
- STRONG_SELL: -6.0

Since 3.5 > 1.0 but not > 6.0, the signal is **BUY**.

---

### Bear Market Instruments

Special handling for inverse instruments that act as market hedges:

**Instruments:**
- **VX** (VIX Futures): Volatility/fear gauge
- **DX** (Dollar Index): Safe haven currency
- **GC** (Gold): Safe haven metal
- **ZB** (30-Year Treasury Bond): Flight to safety

**Inverted Logic:**
When these instruments go UP, it typically indicates bearish sentiment (market fear/uncertainty), so their signal weights are inverted in composite calculations:

```
Standard:           Bear Market Instrument:
STRONG_BUY: +2  →   STRONG_BUY: -2
BUY: +1         →   BUY: -1
HOLD: 0         →   HOLD: 0
SELL: -1        →   SELL: +1
STRONG_SELL: -2 →   STRONG_SELL: +2
```

**Rationale:** Rising VIX = market fear = bearish for equities

---

### Composite Score Calculation

The weighted composite score aggregates all instrument signals:

**Step 1: Calculate Signal Weight Sum**
```
signal_weight_sum = Σ(signal_weight[i])
```

**Step 2: Classify Composite Signal**
```
if signal_weight_sum > 9:
    composite_signal = "STRONG_BUY"
elif signal_weight_sum > 3 and <= 9:
    composite_signal = "BUY"
elif signal_weight_sum >= -3 and <= 3:
    composite_signal = "HOLD"
elif signal_weight_sum < -3 and >= -9:
    composite_signal = "SELL"
elif signal_weight_sum < -9:
    composite_signal = "STRONG_SELL"
```

**Example:**
```
11 instruments:
- 6 instruments with BUY (+1 each) = +6
- 3 instruments with HOLD (0 each) = 0
- 2 instruments with SELL (-1 each) = -2
Signal Weight Sum = +4
Composite Signal = BUY
```

---

## Data Flow

### 1. Data Ingestion (TOS Excel RTD)

```
Excel File (CleanData.xlsm)
    ↓
LiveData/tos Endpoint
    ↓
Redis Cache
    ↓
FutureTrading LatestQuotesView
```

**Configuration (config.py):**
```python
TOS_EXCEL_FILE = r"A:\Thor\CleanData.xlsm"
TOS_EXCEL_SHEET = "Futures"
TOS_EXCEL_RANGE = "A1:M12"  # Headers + 11 instruments
```

**Expected Instruments:**
- YM (Dow Jones E-mini)
- ES (S&P 500 E-mini)
- NQ (Nasdaq 100 E-mini)
- RTY (Russell 2000 E-mini)
- CL (Crude Oil)
- SI (Silver)
- HG (Copper)
- GC (Gold)
- VX (VIX Futures)
- DX (Dollar Index)
- ZB (30-Year Treasury Bond)

---

### 2. Data Enrichment Pipeline

```
Raw TOS Quote
    ↓
Symbol Normalization (RT → RTY, etc.)
    ↓
Transform to MarketData Structure
    ↓
Apply Signal Classification (enrich_quote_row)
    ↓
Compute Derived Metrics (compute_row_metrics)
    ↓
Calculate Composite Score (compute_composite)
    ↓
Return Enriched JSON Response
```

---

### 3. Service Layer

#### services/classification.py

**Functions:**

- `classify(symbol, net_change)`: Core classification logic
  - Returns: (signal, stat_value, contract_weight, signal_weight)
  - Handles bear market instrument inversions
  
- `enrich_quote_row(row)`: Mutates row dict to add signal/stat/weights
  - Adds `extended_data.signal`, `extended_data.stat_value`, etc.
  
- `compute_composite(rows)`: Aggregates all rows into composite score
  - Returns: {sum_weighted, avg_weighted, composite_signal, ...}

**Caching:**
- Uses `@lru_cache` to minimize database queries
- Caches stat maps, weights, and signal weights per symbol

---

#### services/metrics.py

**Function:**

- `compute_row_metrics(row)`: Calculates derived numeric fields
  - `last_prev_diff`: Last price - Previous close
  - `last_prev_pct`: Percentage change
  - `open_prev_diff`, `open_prev_pct`: Open vs previous close
  - `high_prev_diff`, `high_prev_pct`: High vs previous close
  - `low_prev_diff`, `low_prev_pct`: Low vs previous close
  - `range_diff`: High - Low
  - `range_pct`: Range as % of previous close
  - `spread`: Ask - Bid

**Null Handling:** Returns None for missing/invalid data

---

## Configuration

### Symbol Aliases

Handles discrepancies between TOS and database symbols:

```python
SYMBOL_ALIASES = {
    'RT': 'RTY',  # Russell 2000
    '30YrBond': 'ZB',
    'T-BOND': 'ZB',
}
```

### Fallback Stat Map

Hard-coded defaults used when SignalStatValue records are missing:

```python
FALLBACK_STAT_MAP = {
    'YM': {'STRONG_BUY': 60, 'BUY': 10, 'HOLD': 0, 'SELL': -10, 'STRONG_SELL': -60},
    'ES': {'STRONG_BUY': 6, 'BUY': 1, 'HOLD': 0, 'SELL': -1, 'STRONG_SELL': -6},
    'NQ': {'STRONG_BUY': 15, 'BUY': 2.5, 'HOLD': 0, 'SELL': -2.5, 'STRONG_SELL': -15},
    # ... etc
}
```

---

## Django Admin

The module provides comprehensive Django admin panels for managing all models:

### TradingInstrumentAdmin

**Features:**
- List display: symbol, name, category, exchange, active status
- Filters: category, active status, watchlist, exchange
- Inline editing: signal stat values, contract weights
- Fieldsets: organized sections for basic, market, trading, display, and API configuration

### SignalStatValueAdmin

**Features:**
- List display: instrument, signal, value
- Filters: signal type, instrument category
- Inline editing: value field
- Bulk editing support

### ContractWeightAdmin

**Features:**
- List display: instrument, weight
- Filters: instrument category
- Inline editing: weight field

### SignalWeightAdmin

**Features:**
- List display: signal, weight
- Inline editing: weight field
- Ordering: by weight (descending)

---

## Frontend Integration

The module is consumed by the React-based futures trading dashboard at:
```
thor-frontend/src/pages/FutureTrading/FutureTrading.tsx
```

**Key Features:**
- 6x2 grid layout for 11 futures (12th slot reserved)
- Real-time updates with signal indicators
- Color-coded buy/sell signals
- Composite market sentiment header
- Level 1 market data display (bid/ask/last with sizes)
- Historical high/low tracking
- Volume indicators

---

## Testing

### Unit Tests (tests.py)

**MetricsHelperTests:**
- `test_basic_metrics`: Validates derived metric calculations
- `test_handles_missing_and_zero_baseline`: Null/zero handling

**Running Tests:**
```bash
cd thor-backend
python manage.py test FutureTrading
```

---

## Setup & Installation

### 1. Database Migration

```bash
python manage.py makemigrations FutureTrading
python manage.py migrate FutureTrading
```

### 2. Initial Data Setup

Create instrument categories, instruments, and configure signal stat values via Django admin:

```
http://localhost:8000/admin/FutureTrading/
```

### 3. Load Default Signal Weights

Use Django shell or management command to populate SignalWeight table:

```python
from FutureTrading.models import SignalWeight

SignalWeight.objects.create(signal='STRONG_BUY', weight=2)
SignalWeight.objects.create(signal='BUY', weight=1)
SignalWeight.objects.create(signal='HOLD', weight=0)
SignalWeight.objects.create(signal='SELL', weight=-1)
SignalWeight.objects.create(signal='STRONG_SELL', weight=-2)
```

### 4. Configure TOS Excel Integration

Update `config.py` with your Excel file path:

```python
TOS_EXCEL_FILE = r"A:\Thor\CleanData.xlsm"
```

Ensure LiveData/tos endpoint is properly configured and TOS RTD is actively updating the Excel file.

---

## Dependencies

### Backend:
- Django 4.x+
- Django REST Framework
- Redis (for caching)
- Requests (for internal API calls)

### Data Sources:
- TOS (ThinkOrSwit Excel RTD feed
- LiveData/tos endpoint (internal)

---

## URL Configuration

**Module URLs (urls.py):**
```python
urlpatterns = [
    path('quotes/latest', LatestQuotesView.as_view(), name='quotes-latest'),
]
```

**Project URLs (thor_project/urls.py):**
```python
path('api/futuretrading/', include('FutureTrading.urls')),
```

**Full Endpoint:**
```
http://localhost:8000/api/futuretrading/quotes/latest
```

---

## Error Handling

### View-Level Error Handling

```python
try:
    # Data processing
    return Response(data, status=200)
except Exception as e:
    logger.error(f"Error in LatestQuotesView: {str(e)}")
    return Response({
        'error': 'Internal server error',
        'detail': str(e)
    }, status=500)
```

### Service-Level Error Handling

- Graceful degradation when SignalStatValue records are missing (fallback to FALLBACK_STAT_MAP)
- Returns `(None, None, weight, 0)` for unparseable net_change values
- Metric computation failures logged but don't halt enrichment

---

## Performance Considerations

### Caching Strategy

**LRU Cache:**
```python
@lru_cache(maxsize=256)
def _get_stat_map_for_symbol(symbol: str) -> dict:
    # Minimizes DB queries for frequently accessed symbols
```

**Redis Integration:**
- LiveData/tos endpoint caches RTD data
- Reduces Excel file access overhead

### Optimization Tips

1. **Batch Queries:** Use `.select_related()` and `.prefetch_related()` for foreign keys
2. **Index Fields:** Ensure `symbol` fields are indexed
3. **Limit Query Scope:** Only fetch active instruments
4. **Async Processing:** Consider Celery for heavier computations

---

## Future Enhancements

### Planned Features

1. **Historical Data Storage:**
   - Archive quotes to TimescaleDB
   - Enable backtesting and performance analysis

2. **Advanced Analytics:**
   - Volatility calculations
   - Correlation matrices
   - Risk metrics

3. **Multi-Provider Support:**
   - Schwab API integration
   - Polygon.io fallback
   - Provider failover logic

4. **Machine Learning:**
   - Predictive signal classification
   - Sentiment analysis from news feeds

5. **Alerts & Notifications:**
   - Price alerts
   - Signal change notifications
   - Composite threshold alerts

6. **Custom Timeframes:**
   - Support 1min, 5min, 15min, 1hr aggregations
   - Intraday vs daily signal classification

---

## Troubleshooting

### Common Issues

**1. No data returned / Empty rows array**

**Possible Causes:**
- TOS Excel file not updating
- LiveData/tos endpoint unavailable
- No active instruments in database

**Solutions:**
```bash
# Check TOS endpoint
curl http://localhost:8000/api/feed/tos/quotes/latest/?consumer=futures_trading

# Verify Excel file path
python manage.py shell
>>> from FutureTrading.config import TOS_EXCEL_FILE
>>> import os
>>> os.path.exists(TOS_EXCEL_FILE)

# Check active instruments
python manage.py shell
>>> from FutureTrading.models import TradingInstrument
>>> TradingInstrument.objects.filter(is_active=True).count()
```

---

**2. Signals not appearing / All signals are None**

**Possible Causes:**
- Missing SignalStatValue records
- Net change field is None/missing
- Symbol mismatch (aliases not configured)

**Solutions:**
```python
# Check SignalStatValue coverage
from FutureTrading.models import SignalStatValue, TradingInstrument

for inst in TradingInstrument.objects.filter(is_active=True):
    count = SignalStatValue.objects.filter(instrument=inst).count()
    print(f"{inst.symbol}: {count} stat values (need 5)")
    
# Populate missing values via admin or script
```

---

**3. Composite score incorrect**

**Possible Causes:**
- Missing ContractWeight records
- Missing SignalWeight records
- Bear market instruments not inverted

**Solutions:**
```python
# Check ContractWeight coverage
from FutureTrading.models import ContractWeight, TradingInstrument

for inst in TradingInstrument.objects.filter(is_active=True):
    try:
        cw = ContractWeight.objects.get(instrument=inst)
        print(f"{inst.symbol}: {cw.weight}")
    except ContractWeight.DoesNotExist:
        print(f"{inst.symbol}: MISSING weight (defaults to 1.0)")
        
# Check SignalWeight
from FutureTrading.models import SignalWeight
SignalWeight.objects.all().values('signal', 'weight')
```

---

**4. Symbol normalization issues**

**Problem:** Symbol from TOS doesn't match database (e.g., "RT" vs "RTY")

**Solution:** Add to SYMBOL_ALIASES in `services/classification.py`:
```python
SYMBOL_ALIASES = {
    'RT': 'RTY',
    '30YrBond': 'ZB',
    # Add more as needed
}
```

---

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Document complex logic with inline comments
- Keep service functions pure (no side effects)

### Adding New Instruments

1. Create InstrumentCategory (if new asset class)
2. Create TradingInstrument record
3. Add 5 SignalStatValue records (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
4. Add ContractWeight record (default: 1.0)
5. Update config.py EXPECTED_FUTURES if applicable
6. Add symbol alias if needed

### Modifying Classification Logic

1. Update `services/classification.py`
2. Clear LRU cache decorators or restart Django
3. Update tests to cover new logic
4. Document changes in this file

---

## API Examples

### cURL Examples

**Get Latest Quotes:**
```bash
curl http://localhost:8000/api/futuretrading/quotes/latest
```

**With Authentication (if enabled):**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/futuretrading/quotes/latest
```

### JavaScript/Fetch Example

```javascript
fetch('http://localhost:8000/api/futuretrading/quotes/latest')
  .then(res => res.json())
  .then(data => {
    console.log('Composite Signal:', data.total.composite_signal);
    console.log('Instruments:', data.rows.length);
    
    data.rows.forEach(row => {
      console.log(`${row.instrument.symbol}: ${row.extended_data.signal} @ ${row.price}`);
    });
  });
```

---

## Logging

The module uses Python's standard logging framework:

```python
import logging
logger = logging.getLogger(__name__)

# Example log statements
logger.info(f"Fetched {len(raw_quotes)} quotes from TOS Excel")
logger.warning(f"TOS endpoint returned {response.status_code}")
logger.error(f"Failed to fetch TOS data: {e}")
```

**Configuration (settings.py):**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'FutureTrading': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## Related Modules

### LiveData/tos
Provides raw Excel RTD data via `/api/feed/tos/quotes/latest/`

**See:** `LiveData/tos/README.md`

### SchwabLiveData
Alternative data source using Schwab API (future integration)

**See:** `SchwabLiveData/README.md`

### StockTrading
Similar module for equities trading (different classification logic)

**See:** `StockTrading.md`

---

## Maintenance

### Regular Tasks

1. **Monitor Data Quality:**
   - Verify TOS Excel file updates
   - Check for stale timestamps
   - Validate signal distributions

2. **Database Cleanup:**
   - Archive old ContractWeight changes
   - Review and update SignalStatValue thresholds
   - Prune inactive instruments

3. **Performance Monitoring:**
   - Check LRU cache hit rates
   - Monitor API response times
   - Review error logs

### Quarterly Review

- Adjust SignalStatValue thresholds based on market volatility
- Review and update ContractWeight allocations
- Update documentation with new features

---

## Support & Contact

For issues, questions, or feature requests related to FutureTrading:

1. Check this documentation
2. Review existing GitHub issues
3. Check logs for error details
4. Contact development team

---

## Changelog

### Version 1.0 (Current)
- Initial release with TOS Excel RTD integration
- Signal classification with 5 levels
- Weighted composite scoring
- Bear market instrument inversions
- Django admin panels
- RESTful API endpoint

---

## License

This module is part of the Thor trading platform. See main project LICENSE file.

---

## Appendix

### Signal Stat Value Reference Table

| Instrument | STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL | Description |
|------------|------------|-----|------|------|-------------|-------------|
| YM | 60 | 10 | 0 | -10 | -60 | Dow Jones E-mini (points) |
| ES | 6 | 1 | 0 | -1 | -6 | S&P 500 E-mini (points) |
| NQ | 15 | 2.5 | 0 | -2.5 | -15 | Nasdaq 100 E-mini (points) |
| RTY | 15 | 2.5 | 0 | -2.5 | -15 | Russell 2000 E-mini (points) |
| CL | 0.3 | 0.05 | 0 | -0.05 | -0.3 | Crude Oil ($/barrel) |
| SI | 0.06 | 0.01 | 0 | -0.01 | -0.06 | Silver ($/oz) |
| HG | 0.012 | 0.002 | 0 | -0.002 | -0.012 | Copper ($/lb) |
| GC | 3 | 0.5 | 0 | -0.5 | -3 | Gold ($/oz) |
| VX | 0.05 | 0.03 | 0 | -0.03 | -0.05 | VIX Futures (points) |
| DX | 30 | 5 | 0 | -5 | -30 | Dollar Index (points) |
| ZB | 30 | 5 | 0 | -5 | -30 | 30-Year Treasury Bond (points) |

### Database Schema

```sql
-- InstrumentCategory
CREATE TABLE FutureTrading_instrumentcategory (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    color_primary VARCHAR(7) DEFAULT '#4CAF50',
    color_secondary VARCHAR(7) DEFAULT '#81C784',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TradingInstrument
CREATE TABLE FutureTrading_tradinginstrument (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES FutureTrading_instrumentcategory(id),
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE,
    is_watchlist BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    display_precision INTEGER DEFAULT 2,
    tick_size DECIMAL(10,6),
    contract_size DECIMAL(15,2),
    api_provider VARCHAR(50),
    api_symbol VARCHAR(100),
    update_frequency INTEGER DEFAULT 5,
    last_updated TIMESTAMP,
    is_market_open BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- SignalStatValue
CREATE TABLE FutureTrading_signalstatvalue (
    id SERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES FutureTrading_tradinginstrument(id),
    signal VARCHAR(20) NOT NULL,
    value DECIMAL(10,6) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(instrument_id, signal)
);

-- SignalWeight
CREATE TABLE FutureTrading_signalweight (
    id SERIAL PRIMARY KEY,
    signal VARCHAR(20) UNIQUE NOT NULL,
    weight INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ContractWeight
CREATE TABLE FutureTrading_contractweight (
    id SERIAL PRIMARY KEY,
    instrument_id INTEGER UNIQUE REFERENCES FutureTrading_tradinginstrument(id),
    weight DECIMAL(8,6) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

**Document Version:** 1.0  
**Last Updated:** October 25, 2025  
**Author:** Thor Development Team
