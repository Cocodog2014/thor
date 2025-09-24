# Thor Development Guide

## Architecture Overview

Thor is a financial trading dashboard built with Django (backend) and React+Vite (frontend), focusing on futures market data visualization and analysis.

### Core Architectural Principles

1. **SchwabLiveData App** - Controls ALL live data and formatting
2. **FuturesTrading App** - Contains ALL formulas and business logic
3. **Clean Separation** - No cross-contamination of responsibilities

## Application Structure

```
thor-backend/
├── SchwabLiveData/          # Live Data & Formatting Layer
│   ├── providers.py         # Data providers (Excel, JSON, Schwab API)
│   ├── excel_live.py        # Real-time Excel integration
│   ├── views.py            # API endpoints for live quotes
│   └── provider_factory.py  # Provider selection logic
├── futuretrading/          # Business Logic & Formulas Layer
│   ├── models.py           # Trading instruments, signals, weights
│   ├── views.py            # Enriched quotes with classifications
│   └── services/
│       └── classification.py # Signal classification formulas
├── timezones/              # Deployment & Scheduling Control
│   ├── models.py           # Market hours, deployment schedules
│   ├── views.py            # Timezone-aware APIs
│   └── services/           # Market timing logic
├── thordata/               # Backtesting & Historical Analysis
│   ├── models.py           # Historical data, backtest results
│   ├── views.py            # Backtesting APIs
│   └── services/           # Backtesting engines
└── thor_project/           # Django settings

thor-frontend/
├── src/
│   ├── pages/
│   │   └── FutureTrading/   # Main dashboard
│   ├── components/         # Reusable UI components  
│   └── services/          # API client logic
└── package.json
```

## Responsibility Matrix

### SchwabLiveData App - "Data Source Truth"
**Owns:** Raw market data delivery and display formatting

- ✅ **Live Data Providers**
  - Excel Live (xlwings integration)
  - Excel File (openpyxl static reading)
  - JSON Mock Data
  - Future: Schwab API integration

- ✅ **Data Formatting**
  - Symbol-specific display precision (YM=0, ES=2, SI=3, etc.)
  - Price rounding and string conversion
  - Field standardization (bid/ask/last/volume)

- ✅ **API Endpoints**
  - `/api/schwab/quotes/latest/` - Primary live data feed
  - Provider health checks and status

- ❌ **Does NOT Handle**
  - Signal classification (Strong Buy/Sell/Hold)
  - Statistical value calculations
  - Contract weighting formulas
  - Composite score computations

### FuturesTrading App - "Business Logic Truth"
**Owns:** All trading formulas and derived calculations

- ✅ **Trading Models**
  - TradingInstrument, TradingSignal, MarketData
  - SignalStatValue (maps signals to numeric values)
  - ContractWeight (instrument weighting factors)
  - HbsThresholds (classification boundaries)

- ✅ **Classification Formulas** (`services/classification.py`)
  - Net change → Signal mapping (Strong Buy/Buy/Hold/Sell/Strong Sell)
  - Statistical value lookups per instrument
  - Weighted composite calculations

- ✅ **API Endpoints**
  - `/api/quotes/latest/` - Enriched quotes with signals/weights
  - Strategy definition and management APIs
  - Real-time signal generation endpoints

- ❌ **Does NOT Handle**
  - Raw data collection
  - Display precision decisions
  - Provider selection logic
  - Deployment timing or scheduling
  - Historical data backtesting

### Timezones App - "Deployment & Scheduling Control"
**Owns:** When and how features are deployed and activated

- ✅ **Market Timing**
  - Market open/close schedules per exchange
  - Trading session awareness (pre-market, regular, after-hours)
  - Holiday calendar management
  - Timezone conversions for global markets

- ✅ **Deployment Control**
  - Feature deployment schedules
  - Market-hours-aware feature activation
  - Rollback timing windows
  - Maintenance window scheduling

- ✅ **Time-Based Logic**
  - When to start/stop data collection
  - When to activate trading signals
  - When to send alerts or notifications
  - Session-based feature toggles

- ❌ **Does NOT Handle**
  - Trading calculations or formulas
  - Raw data formatting
  - User interface logic
  - Historical data analysis

### Thordata App - "Backtesting & Historical Analysis"
**Owns:** All historical data processing and backtesting functionality

- ✅ **Historical Data Management**
  - Historical price data storage and retrieval
  - Data archiving and compression
  - Historical market data APIs
  - Data quality validation and cleaning

- ✅ **Backtesting Engine**
  - Strategy backtesting framework
  - Historical signal generation
  - Performance metrics calculation
  - Risk analysis and drawdown calculations

- ✅ **Analysis Tools**
  - Historical pattern recognition
  - Statistical analysis of trading strategies
  - Performance comparison tools
  - Portfolio simulation capabilities

- ✅ **API Endpoints**
  - Historical data retrieval APIs
  - Backtesting execution endpoints
  - Performance reporting APIs
  - Strategy comparison tools

- ❌ **Does NOT Handle**
  - Live data collection or formatting
  - Real-time signal generation
  - Deployment timing or scheduling
  - Current market data processing

## Data Flow Architecture

### Live Data Flow
```
Excel/API Data → SchwabLiveData → FuturesTrading → Frontend
                 (formatting)     (classification)  (display)
                      ↑                ↑
                 Timezones ←──────────── Timezones
                 (schedule)           (timing)
```

### Historical Data Flow
```
Historical Data → Thordata → FuturesTrading → Frontend
                 (backtesting) (strategies)   (results)
                      ↑
                 Timezones
                 (schedule)
```

### Combined Flow
1. **Timezones** determines when data collection should be active
2. **SchwabLiveData** fetches raw quotes with proper formatting (when scheduled)
3. **FuturesTrading** enriches with signals/weights (when market is open)
4. **Thordata** processes historical data and runs backtests (scheduled)
5. **Frontend** renders both live data and backtest results
```

## Development Setup

### Backend (Django)

1. **Environment Setup**
   ```powershell
   cd A:\Thor\thor-backend
   .\venv\Scripts\Activate.ps1
   ```

2. **Environment Variables**
   ```powershell
   # Primary data source
   $env:DATA_PROVIDER = 'excel_live'  # or 'excel', 'json', 'schwab'
   
   # Excel Live settings
   $env:EXCEL_DATA_FILE = 'A:\Thor\CleanData.xlsm'
   $env:EXCEL_SHEET_NAME = 'Futures'
   $env:EXCEL_LIVE_RANGE = 'A1:M20'
   $env:EXCEL_LIVE_REQUIRE_OPEN = '0'
   ```

3. **Database Setup**
   ```powershell
   python manage.py migrate
   python manage.py seed_stat_values --create-instruments
   ```

4. **Start Server**
   ```powershell
   python manage.py runserver
   ```

### Frontend (React + Vite)

1. **Setup**
   ```powershell
   cd A:\Thor\thor-frontend
   npm install
   ```

2. **Development Server**
   ```powershell
   npm run dev
   ```

3. **Access URLs**
   - Frontend: http://localhost:5173
   - Backend API: http://127.0.0.1:8000/api/
   - Admin: http://127.0.0.1:8000/admin/

## API Endpoints

### SchwabLiveData Endpoints
- `GET /api/schwab/quotes/latest/` - Raw formatted live data
  - Query params: `provider`, `excel_file`, `sheet_name`, `live_sim`
  - Returns: Raw quotes with display formatting applied

### FuturesTrading Endpoints  
- `GET /api/quotes/latest/` - Enriched data with signals/weights
  - Includes classification results and composite calculations
  - Uses SchwabLiveData as data source + adds business logic

## Development Patterns

### Adding New Data Fields

**For Raw Data Fields (prices, volumes, etc.):**
1. Update SchwabLiveData providers
2. Add to provider data structure
3. Handle formatting/precision rules

**For Derived Fields (signals, ratios, etc.):**
1. Update FuturesTrading models/services
2. Add to classification.py or new service module
3. Enrich in LatestQuotesView

### Provider Development

**Adding New Data Sources:**
1. Create provider class in `SchwabLiveData/providers.py`
2. Implement `BaseProvider` interface
3. Register in `create_provider()` factory
4. Add configuration to `ProviderConfig`

### Formula Development

**Adding New Classifications:**
1. Extend `futuretrading/services/classification.py`
2. Add database models if persistent storage needed
3. Create management commands for data seeding
4. Add admin interfaces for configuration

## Testing Strategy

### SchwabLiveData Testing
- Test each provider independently
- Mock external data sources (Excel, APIs)
- Verify formatting consistency across providers
- Test provider fallback mechanisms

### FuturesTrading Testing
- Test classification formulas with known inputs
- Verify statistical value calculations
- Test composite score computations
- Mock SchwabLiveData responses for isolation

### Integration Testing
- End-to-end data flow testing
- Frontend API contract validation
- Real-time data update verification

## Deployment Considerations

### Environment Configuration
- Production should use Schwab API provider
- Staging can use Excel or JSON providers
- Development defaults to Excel Live for real-time testing

### Performance Optimization
- Provider result caching (already implemented)
- Database query optimization for large datasets
- Frontend polling rate configuration

### Monitoring
- Provider health check endpoints
- Data freshness monitoring
- Classification accuracy tracking

## Future Enhancements

### SchwabLiveData Roadmap
- Full Schwab API integration
- WebSocket real-time feeds
- Multiple exchange support
- Historical data providers

### FuturesTrading Roadmap  
- Advanced signal algorithms
- Real-time risk management formulas
- Portfolio optimization tools
- Alert system integration
- Strategy performance monitoring

### Timezones Roadmap
- Market hours automation
- Deployment scheduling system
- Holiday calendar integration
- Global market timezone support
- Feature rollout timing controls

### Thordata Roadmap
- Complete backtesting framework
- Historical data ingestion pipelines
- Strategy performance analytics
- Risk-adjusted return calculations
- Portfolio simulation tools
- Monte Carlo analysis capabilities

## Common Development Tasks

### Changing Display Precision
Update the precision maps in:
- `SchwabLiveData/providers.py` (ExcelProvider)
- `SchwabLiveData/providers.py` (JSONProvider) 
- `SchwabLiveData/excel_live.py` (ExcelLiveProvider)

### Adding New Futures Contracts
1. Add to `DEFAULT_SYMBOLS` in ProviderConfig
2. Add stat values via `seed_stat_values` command
3. Add precision rules to provider precision maps
4. Configure market hours in timezones app
5. Update frontend symbol list if needed

### Modifying Classification Logic
1. Update `futuretrading/services/classification.py`
2. Adjust threshold values in database or fallback constants
3. Test with known market scenarios
4. Update admin interfaces for configuration

### Scheduling Feature Deployments
1. Define deployment windows in timezones app
2. Configure market-hours-aware activation
3. Set rollback timing constraints
4. Test deployment timing logic
5. Monitor deployment success across timezones

### Running Backtests
1. Define strategy parameters in futuretrading app
2. Load historical data via thordata app
3. Execute backtest using thordata engines
4. Analyze results through thordata APIs
5. Compare strategy performance metrics
6. Schedule regular backtest runs via timezones

---

## Quick Reference

**Start Development:**
```powershell
# Terminal 1 - Backend
cd A:\Thor\thor-backend
.\venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 2 - Frontend  
cd A:\Thor\thor-frontend
npm run dev
```

**Key Files to Know:**
- Live Data Flow: `SchwabLiveData/views.py` → `futuretrading/views.py`
- Historical Data Flow: `thordata/views.py` → `futuretrading/views.py`
- Providers: `SchwabLiveData/providers.py`, `SchwabLiveData/excel_live.py`
- Classification: `futuretrading/services/classification.py`
- Backtesting: `thordata/services/` (to be implemented)
- Frontend: `src/pages/FutureTrading/FutureTrading.tsx`
- Models: `futuretrading/models.py`, `thordata/models.py`

**Common URLs:**
- Live Data API: `/api/schwab/quotes/latest/`
- Enriched API: `/api/quotes/latest/`
- Historical Data API: `/api/thordata/` (to be implemented)
- Backtesting API: `/api/thordata/backtest/` (to be implemented)
- Admin Panel: `/admin/`
- Frontend: `http://localhost:5173`