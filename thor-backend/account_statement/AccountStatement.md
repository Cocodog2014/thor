# Account Statement App Documentation

## Overview

The Account Statement app provides comprehensive trading account management for the Thor trading platform. It supports both paper trading accounts (for practice) and real money accounts (connected to actual brokerages), with detailed financial tracking and risk management features.

## Architecture

### Modular Design

The app follows a modular architecture with separate components for different account types:

```
account_statement/
├── models/
│   ├── __init__.py          # Model exports
│   ├── base.py              # BaseAccount & AccountSummary
│   ├── paper.py             # PaperAccount model
│   └── real.py              # RealAccount model
├── views/
│   ├── __init__.py          # View exports
│   ├── base.py              # Shared views & mixins
│   ├── paper.py             # Paper account views
│   └── real.py              # Real account views
├── urls/
│   ├── __init__.py          # URL exports
│   ├── base.py              # Main routing
│   ├── paper.py             # Paper account URLs
│   └── real.py              # Real account URLs
├── admin.py                 # Django admin configuration
└── apps.py                  # App configuration
```

## Models

### BaseAccount (Abstract)

Abstract base class containing common fields for all trading accounts:

**Core Fields:**
- `user` (FK to CustomUser) - Account owner
- `account_number` (CharField) - Unique account identifier
- `base_currency` (CharField) - Default: USD
- `status` (CharField) - ACTIVE/CLOSED/SUSPENDED/PENDING

**Financial Fields (from Schwab statement):**
- `net_liquidating_value` - Total account value if liquidated
- `stock_buying_power` - Available funds for stock purchases
- `option_buying_power` - Available funds for options
- `available_funds_for_trading` - Available trading funds
- `long_stock_value` - Value of long stock positions
- `long_marginable_value` - Value of long marginable securities
- `short_marginable_value` - Value of short marginable securities
- `margin_equity` - Equity available for margin trading
- `equity_percentage` - Equity percentage (0-100)
- `maintenance_requirement` - Minimum equity required
- `money_market_balance` - Cash in money market fund

**Commission Tracking:**
- `equity_commissions_fees_ytd` - YTD equity fees
- `option_commissions_fees_ytd` - YTD option fees
- `futures_commissions_fees_ytd` - YTD futures fees
- `total_commissions_fees_ytd` - Total YTD fees (calculated)

### PaperAccount

Paper trading account for virtual trading practice.

**Additional Fields:**
- `starting_balance` (Decimal) - Default: $100,000
- `reset_count` (Integer) - Number of account resets
- `last_reset_date` (DateTime) - Last reset timestamp

**Key Features:**
- One paper account per user (database constraint)
- Account reset functionality
- Performance tracking vs starting balance
- Automatic initialization with starting balance

**Methods:**
- `reset_account()` - Reset to starting balance and clear positions
- `get_performance_summary()` - Calculate performance metrics

### RealAccount

Real money trading account connected to actual brokerages.

**Brokerage Integration:**
- `brokerage_provider` (CharField) - SCHWAB/IB/TDA/FIDELITY/OTHER
- `external_account_id` (CharField) - Brokerage account ID
- `account_nickname` (CharField) - User-defined name

**Verification & API:**
- `is_verified` (Boolean) - Account verification status
- `verification_date` (DateTime) - When verified
- `api_enabled` (Boolean) - API access configured
- `last_sync_date` (DateTime) - Last API sync
- `sync_errors` (Integer) - Consecutive sync failures

**Trading Permissions:**
- `day_trading_enabled` (Boolean) - Day trading allowed
- `margin_enabled` (Boolean) - Margin trading allowed
- `options_level` (Integer) - Options trading level (0-4)

**Risk Management:**
- `daily_loss_limit` (Decimal) - Maximum daily loss
- `position_size_limit` (Decimal) - Maximum position size

**Methods:**
- `sync_with_brokerage()` - Sync with brokerage API
- `can_day_trade()` - Check PDT rule compliance
- `can_trade_options()` - Check options permissions
- `get_risk_status()` - Get risk management status

### AccountSummary

Historical snapshots of account performance.

**Fields:**
- `content_type` & `object_id` - Generic FK to account
- `statement_date` (DateTime) - Snapshot timestamp
- `pnl_open` (Decimal) - Unrealized P&L
- `pnl_day` (Decimal) - Daily P&L
- `pnl_ytd` (Decimal) - Year-to-date P&L
- `pnl_percent` (Decimal) - P&L percentage
- `margin_requirement` (Decimal) - Margin requirement
- `mark_value` (Decimal) - Mark-to-market value
- `net_liquidating_value_snapshot` (Decimal) - Account value snapshot

## Views

### Base Views

**AccountOwnerMixin:**
- Ensures users only access their own accounts
- Automatic user assignment on creation

**AccountListView:**
- Base list view for accounts
- Pagination and filtering support

**AccountDetailView:**
- Base detail view with performance metrics
- Recent summaries display

**account_dashboard:**
- Overview of all user accounts
- Summary statistics

### Paper Account Views

**PaperAccountListView:**
- List all user's paper accounts
- Create account option (if none exists)

**PaperAccountDetailView:**
- Paper account details
- Reset functionality access

**PaperAccountCreateView:**
- Create new paper account
- Prevents multiple paper accounts per user

**paper_account_reset:**
- Reset account to starting balance
- Confirmation required

**paper_account_performance:**
- AJAX endpoint for performance data
- Chart-ready JSON response

### Real Account Views

**RealAccountListView:**
- List all user's real accounts
- Multiple accounts supported

**RealAccountDetailView:**
- Real account details
- Verification and sync status

**RealAccountCreateView:**
- Create new real account
- Brokerage configuration

**real_account_sync:**
- Sync with brokerage API
- Error handling and reporting

**real_account_verify:**
- Account verification process
- Integration placeholder

## URL Structure

### Main Routes
- `/account-statement/` - Dashboard
- `/account-statement/paper/` - Paper accounts
- `/account-statement/real/` - Real accounts

### Paper Account URLs
- `GET /paper/` - List paper accounts
- `GET /paper/create/` - Create paper account
- `GET /paper/{id}/` - Paper account detail
- `POST /paper/{id}/reset/` - Reset paper account
- `GET /paper/{id}/performance/` - Performance data (AJAX)

### Real Account URLs
- `GET /real/` - List real accounts
- `GET /real/create/` - Create real account
- `GET /real/{id}/` - Real account detail
- `POST /real/{id}/sync/` - Sync with brokerage
- `POST /real/{id}/verify/` - Verify account
- `GET /real/{id}/risk-status/` - Risk status (AJAX)

## API Endpoints

### Base API Features
- Authentication required
- User ownership enforcement
- Common actions: list, create, retrieve, update

### Paper Account API
- `GET /api/paper-accounts/` - List paper accounts
- `POST /api/paper-accounts/` - Create paper account
- `GET /api/paper-accounts/{id}/` - Get paper account
- `POST /api/paper-accounts/{id}/reset/` - Reset account
- `GET /api/paper-accounts/{id}/performance_chart/` - Chart data

### Real Account API
- `GET /api/real-accounts/` - List real accounts
- `POST /api/real-accounts/` - Create real account
- `GET /api/real-accounts/{id}/` - Get real account
- `POST /api/real-accounts/{id}/sync/` - Sync with brokerage
- `POST /api/real-accounts/{id}/verify/` - Verify account
- `GET /api/real-accounts/{id}/risk_status/` - Risk status

## Admin Interface

### PaperAccountAdmin
- **List Display:** User, account number, balance, resets, status
- **Filters:** Status, currency, creation date, reset count
- **Actions:** Bulk reset accounts
- **Fieldsets:** Organized by account info, balances, positions, fees

### RealAccountAdmin
- **List Display:** User, brokerage, balance, verification, API status
- **Filters:** Brokerage, verification, API, trading permissions
- **Actions:** Bulk sync, bulk verify
- **Fieldsets:** Account info, verification, permissions, risk, balances

### AccountSummaryAdmin
- **List Display:** Account info, date, P&L metrics, balance
- **Filters:** Date, content type
- **Read-only:** Calculated fields

## Integration Points

### User Integration
- Extends CustomUser from users app
- Role-based access control
- User ownership enforcement

### Trading System Integration
- Account balance updates from trades
- Position value calculations
- Commission and fee tracking
- P&L calculations

### Brokerage API Integration
- Schwab API support (primary)
- Other brokerage support planned
- Real-time account sync
- Position and balance updates

## Security Features

### Access Control
- User can only access own accounts
- Admin override for support
- API authentication required

### Risk Management
- Daily loss limits
- Position size limits
- PDT rule compliance
- Margin requirement monitoring

### Data Protection
- Sensitive account data encrypted
- API credentials secured
- Audit trail for account changes

## Performance Considerations

### Database Optimization
- Indexes on frequently queried fields
- Select_related for admin queries
- Pagination for large datasets

### API Optimization
- Bulk operations for sync
- Cached performance calculations
- Efficient query patterns

## Testing Strategy

### Unit Tests
- Model validation and calculations
- Account reset functionality
- Performance metric calculations

### Integration Tests
- User account relationships
- API endpoint functionality
- Admin interface operations

### Mock Brokerage Tests
- API sync simulation
- Error handling verification
- Data consistency checks

## Future Enhancements

### Planned Features
- Multi-currency support
- Advanced risk analytics
- Performance benchmarking
- Account sharing/family accounts

### Brokerage Expansion
- Additional brokerage providers
- Unified API abstraction
- Real-time streaming data
- Advanced order types

### Reporting
- Custom date range reports
- Tax reporting integration
- Performance analytics
- Compliance reporting

## Development Notes

### Best Practices
- Separate paper and real account logic
- Use Decimal for financial calculations
- Comprehensive error handling
- Detailed logging for debugging

### Code Organization
- Modular structure for maintainability
- Clear separation of concerns
- Consistent naming conventions
- Comprehensive documentation

### Deployment Considerations
- Environment-specific settings
- API credential management
- Database migration strategy
- Monitoring and alerting