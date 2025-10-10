# SchwabLiveData App Documentation

## Overview

The SchwabLiveData app is responsible for **ALL live market data collection and formatting**. It serves as the single source of truth for raw market data, handling multiple data providers and ensuring consistent formatting across the Thor system.

## Architecture Principle

**SchwabLiveData owns:** Raw data collection, provider management, and display formatting
**SchwabLiveData does NOT own:** Trading formulas, signal classification, or business logic

## File Documentation

### Core Provider System

#### `providers.py`
**Purpose:** Core data provider implementations
- **JSONProvider** - Mock data provider using JSON files for testing/development
- **ExcelProvider** - Static Excel file reader using openpyxl
- **BaseProvider** - Abstract base class defining provider interface
- **Helper functions** - Data parsing, simulation, and formatting utilities

**Key Features:**
- Symbol-specific display precision (YM=0, ES=2, SI=3, etc.)
- Live price simulation for testing
- Consistent data structure across all providers
- Error handling and fallback mechanisms

#### `excel_live.py`  
**Purpose:** Real-time Excel integration using xlwings
- **ExcelLiveProvider** - Live Excel data reader with polling thread
- Connects to running Excel workbooks
- Real-time data updates without file I/O
- Configurable polling intervals and data ranges

**Key Features:**
- Background polling thread for live updates
- Excel workbook connection management  
- Header detection and column mapping
- Symbol canonicalization (handles /YM vs YM variations)

#### `provider_factory.py`
**Purpose:** Provider selection and configuration management
- **ProviderConfig** - Configuration class for provider settings
- **get_market_data_provider()** - Factory function for provider instances
- Provider caching and reuse logic
- Environment variable and request parameter handling

**Key Features:**
- Provider priority and fallback logic
- Configuration validation and defaults
- Provider instance caching for performance
- Support for multiple provider types (excel_live, excel, json, schwab)

### API Layer

#### `views.py`
**Purpose:** REST API endpoints for live market data
- **SchwabQuotesView** - Primary live quotes endpoint (`/api/schwab/quotes/latest/`)
- **ProviderStatusView** - Provider health and configuration info
- **ProviderHealthView** - Simple health check endpoint

**Key Features:**
- Provider-agnostic API interface
- Database enrichment integration (signals/weights from futuretrading app)
- Composite total calculations
- Error handling and status reporting

#### `urls.py`
**Purpose:** URL routing configuration
- Maps API endpoints to view classes
- Defines URL patterns for the SchwabLiveData app

### Data Management

#### `futures_data.json`
**Purpose:** Mock market data for JSONProvider
- Sample futures contract data
- Used for development and testing when live data unavailable
- Includes price, volume, and basic market data fields

#### `update_futures_data.py`
**Purpose:** Utility script for updating mock data
- Updates the futures_data.json file
- Can be used to refresh test data or add new instruments

### Integration Files

#### `schwab_client.py`
**Purpose:** Schwab API client implementation (future use)
- Placeholder for Schwab API integration
- Will handle authentication and API requests when implemented

#### `models.py`
**Purpose:** Django models (currently minimal)
- May contain configuration models in the future
- Currently relies on futuretrading app models for data storage

#### `admin.py`
**Purpose:** Django admin interface configuration
- Admin panels for any SchwabLiveData models
- Configuration interfaces for providers

### Standard Django Files

#### `apps.py`
**Purpose:** Django app configuration
- App registration and configuration
- App-specific settings and initialization

#### `tests.py`  
**Purpose:** Unit tests for the SchwabLiveData app
- Provider testing
- API endpoint testing
- Data formatting validation

#### `__init__.py`
**Purpose:** Python package initialization
- Makes SchwabLiveData a Python package
- Package-level imports and configuration

#### `management/`
**Purpose:** Django management commands
- Custom management commands for data operations
- Provider setup and maintenance commands

#### `migrations/`
**Purpose:** Database migration files
- Database schema changes
- Model evolution history

#### `__pycache__/`
**Purpose:** Python bytecode cache
- Compiled Python files for performance
- Generated automatically by Python

## Data Flow

```
1. provider_factory.py → Selects appropriate provider (Excel Live/File/JSON/Schwab)
2. providers.py → Fetches raw data with proper formatting
3. views.py → Serves formatted data via REST API
4. excel_live.py → (If selected) Provides real-time Excel integration
```

## Key Design Decisions

### Symbol-Specific Precision
All providers implement the same precision mapping:
- `/YM`, `YM` → 0 decimals (whole points)
- `/ES`, `ES`, `/NQ`, `NQ` → 2 decimals (quarter points)  
- `SI` → 3 decimals (half-cent increments)
- `HG` → 4 decimals (0.0005 tick size)

### Provider Abstraction
All providers implement the same interface, allowing seamless switching between:
- Excel Live (real-time xlwings)
- Excel File (static openpyxl)
- JSON Mock (testing/development)
- Schwab API (future implementation)

### Formatting Responsibility
SchwabLiveData handles ALL display formatting, including:
- Price rounding and precision
- String conversion for API responses
- Field standardization across providers
- Data structure consistency

## Integration Points

### With FuturesTrading App
- Views.py enriches raw data with signals/weights from futuretrading models
- No direct model dependencies - uses loose coupling via API

### With Frontend
- Provides `/api/schwab/quotes/latest/` endpoint
- Returns consistently formatted data regardless of provider
- Includes provider health and status information

### With Timezones App (Future)
- Will respect market hours for data collection
- Will handle scheduled data collection windows

## Provider Configuration

### Environment Variables
```bash
# Primary provider selection
DATA_PROVIDER=excel_live  # or excel, json, schwab

# Excel settings
EXCEL_DATA_FILE=A:\Thor\CleanData.xlsm
EXCEL_SHEET_NAME=Futures
EXCEL_LIVE_RANGE=A1:M20
EXCEL_LIVE_REQUIRE_OPEN=0  # 0=auto-open, 1=must be open

# Schwab API (future)
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_secret
SCHWAB_REDIRECT_URI=your_redirect
SCHWAB_SCOPES=read
```

## OAuth quickstart (non-breaking)

We added a minimal OAuth flow that does not call the real token API yet but lets you verify the Schwab app wiring:

1) In `thor-backend/.env`, add your credentials from the Schwab portal:

	- `SCHWAB_CLIENT_ID` = App Key
	- `SCHWAB_CLIENT_SECRET` = Secret
	- `SCHWAB_REDIRECT_URI` = https://360edu.org/auth/callback (matches your portal screenshot)

2) Keep `DATA_PROVIDER=excel_live` so existing Excel data keeps working while you test.

3) Start the backend server, then open this URL to begin the OAuth redirect:

	- `http://localhost:8000/api/schwab/auth/login/`

4) After approving, Schwab will redirect to your callback; our callback echoes the code/state so you can confirm it arrived:

	- `http://localhost:8000/api/schwab/auth/callback?code=...&state=thor`

Once access is fully approved, implement token exchange in `schwab_client.py` and switch `DATA_PROVIDER=schwab` to enable the real provider.

### Provider Options
- **Excel Live** (recommended): Real-time Excel COM integration
- **Excel File**: Static file reading via openpyxl  
- **JSON**: Mock data for development/testing
- **Schwab**: Future API integration (placeholder)
