# 📊 Thor Trading Data - PostgreSQL Implementation

## 🔑 Database Access Credentials

### PostgreSQL Database
- **Host**: localhost
- **Port**: 5433 (external), 5432 (internal container)
- **Database**: thor_db
- **Username**: thor_user
- **Password**: thor_password

### pgAdmin Web Interface
- **URL**: http://localhost:8080
- **Email**: admin@thor.com
- **Password**: admin

### pgAdmin Server Configuration
When adding PostgreSQL server in pgAdmin:
- **Host**: thor_postgres (container name)
- **Port**: 5432 (internal container port)
- **Database**: thor_db
- **Username**: thor_user
- **Password**: thor_password

## Overview
This document outlines the PostgreSQL database structure and implementation for the Thor Trading Data system, which imports and manages large-scale financial trading data with 139+ indicators per record.

## Database Architecture

### Core Tables

#### 1. TradingData Table
**Purpose**: Stores financial trading data using a hybrid approach - key fields as columns, additional indicators as JSON.

```sql
-- Core structure (simplified view)
CREATE TABLE thordata_tradingdata (
    id SERIAL PRIMARY KEY,
    no_trades INTEGER NOT NULL,
    dlst VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    date INTEGER NOT NULL,
    day VARCHAR(20),
    open_price DECIMAL(15,6),
    close_price DECIMAL(15,6),
    volume BIGINT,
    world_net_change DECIMAL(15,6),
    world_net_perc_change DECIMAL(10,4),
    world_high DECIMAL(15,6),
    world_low DECIMAL(15,6),
    additional_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Constraints
    CONSTRAINT unique_trading_record UNIQUE (no_trades, dlst, year, month, date)
);
```

#### 2. ImportJob Table
**Purpose**: Tracks CSV import operations and progress.

```sql
CREATE TABLE thordata_importjob (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);
```

### Indexes for Performance

```sql
-- Primary indexes for fast queries
CREATE INDEX idx_tradingdata_year_month_date ON thordata_tradingdata (year, month, date);
CREATE INDEX idx_tradingdata_dlst_year_month ON thordata_tradingdata (dlst, year, month);
CREATE INDEX idx_tradingdata_no_trades ON thordata_tradingdata (no_trades);
CREATE INDEX idx_tradingdata_volume ON thordata_tradingdata (volume);

-- JSONB indexes for additional_data queries
CREATE INDEX idx_tradingdata_additional_data_gin ON thordata_tradingdata USING GIN (additional_data);

-- Import job indexes
CREATE INDEX idx_importjob_status ON thordata_importjob (status);
CREATE INDEX idx_importjob_created_at ON thordata_importjob (created_at DESC);
```

## Data Model Design Decisions

### Hybrid Approach Rationale
1. **Core Financial Fields as Columns**: Fast queries for common operations (date filtering, price analysis)
2. **Indicators as JSON**: Flexibility for 139+ diverse trading indicators without schema changes
3. **PostgreSQL JSONB**: Efficient storage and indexing of JSON data

### Field Mappings

#### Core Database Columns
```python
# CSV Column -> Database Column
'No._Trades' -> no_trades (INTEGER)
'DLST' -> dlst (VARCHAR(50))
'Year' -> year (INTEGER)
'Month' -> month (INTEGER)  # Converted from "Jan"->1, "Feb"->2, etc.
'Date' -> date (INTEGER)
'Day' -> day (VARCHAR(20))
'OPEN' -> open_price (DECIMAL(15,6))
'CLOSE' -> close_price (DECIMAL(15,6))
'Volume' -> volume (BIGINT)
'WorldNetChange' -> world_net_change (DECIMAL(15,6))
'WorldNetPercChange' -> world_net_perc_change (DECIMAL(10,4))
'WorldHigh' -> world_high (DECIMAL(15,6))
'WorldLow' -> world_low (DECIMAL(15,6))
```

#### JSON Storage (additional_data)
All other 130+ fields stored as key-value pairs:
```json
{
  "AI": 85.3,
  "AiEXCHANGE": "USA",
  "FwStrongBuyWorkerValue": 1234.56,
  "ClpPercentage": 23.4,
  "52WeekHigh": 156.78,
  // ... 130+ more indicators
}
```

## Import System

### CSV Processing Pipeline
1. **File Validation**: Check file exists and is readable
2. **Row Counting**: First pass to count total rows for progress tracking
3. **Data Processing**: Second pass with batch processing
4. **Month Conversion**: "Jan"→1, "Feb"→2, etc.
5. **Type Conversion**: Strings to appropriate numeric types
6. **Batch Insertion**: 1000 records per transaction for performance
7. **Progress Tracking**: Real-time updates via ImportJob model

### Import Command Usage
```bash
# Dry run (test without importing)
python manage.py import_trading_data "path/to/data.csv" --dry-run

# Full import with custom batch size
python manage.py import_trading_data "path/to/data.csv" --batch-size=1000

# Default import
python manage.py import_trading_data "A:\Thor\CleanData-ComputerLearning.csv"
```

## Current Data Statistics
- **Total Records**: 74,139
- **Date Range**: 2019-2025 (6+ years)
- **DLST Types**: 2 (ON/OFF market states)
- **Storage**: ~139 fields per record
- **Core Fields**: 13 database columns
- **JSON Fields**: 130+ indicators in additional_data

## Query Examples

### Basic Queries
```sql
-- Get recent trading data
SELECT no_trades, dlst, year, month, date, open_price, close_price, volume
FROM thordata_tradingdata
WHERE year = 2025 AND month = 1
ORDER BY date DESC, no_trades DESC
LIMIT 10;

-- Get trading volume statistics by year
SELECT year, 
       COUNT(*) as record_count,
       AVG(volume) as avg_volume,
       MAX(volume) as max_volume,
       MIN(volume) as min_volume
FROM thordata_tradingdata
WHERE volume IS NOT NULL
GROUP BY year
ORDER BY year DESC;
```

### JSON Queries
```sql
-- Query specific indicators from JSON
SELECT no_trades, dlst, year, month, date,
       additional_data->>'AI' as ai_indicator,
       additional_data->>'52WeekHigh' as week_high,
       additional_data->>'FwStrongBuyWorkerValue' as strong_buy
FROM thordata_tradingdata
WHERE (additional_data->>'AI')::numeric > 80
LIMIT 10;

-- Find records with specific exchange
SELECT COUNT(*)
FROM thordata_tradingdata
WHERE additional_data->>'AiEXCHANGE' = 'USA';
```

### Performance Queries
```sql
-- Date range query (uses index)
SELECT COUNT(*)
FROM thordata_tradingdata
WHERE year BETWEEN 2024 AND 2025
  AND month BETWEEN 1 AND 6;

-- DLST analysis (uses index)
SELECT dlst, COUNT(*) as record_count
FROM thordata_tradingdata
GROUP BY dlst;
```

## Future Scaling Considerations

### Database Optimization
1. **Partitioning**: Consider partitioning by year for large datasets
```sql
-- Example partitioning strategy
CREATE TABLE thordata_tradingdata_2025 PARTITION OF thordata_tradingdata
FOR VALUES FROM (2025, 1, 1) TO (2026, 1, 1);
```

2. **Additional Indexes**: Add specific indexes based on query patterns
```sql
-- Custom indexes for specific indicators
CREATE INDEX idx_ai_indicator ON thordata_tradingdata 
USING BTREE ((additional_data->>'AI')::numeric);
```

3. **JSON Optimization**: Extract frequently queried JSON fields to columns
```sql
-- Add column for frequently accessed indicator
ALTER TABLE thordata_tradingdata ADD COLUMN ai_indicator DECIMAL(10,4);
UPDATE thordata_tradingdata SET ai_indicator = (additional_data->>'AI')::numeric;
CREATE INDEX idx_ai_indicator_column ON thordata_tradingdata (ai_indicator);
```

### Real-time Data Integration
```sql
-- Structure for real-time updates (10-second intervals)
CREATE TABLE thordata_realtimedata (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(15,6),
    volume BIGINT,
    market_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_realtime_symbol_timestamp ON thordata_realtimedata (symbol, timestamp DESC);
```

## Backup and Maintenance

### Regular Maintenance
```sql
-- Analyze tables for query optimization
ANALYZE thordata_tradingdata;
ANALYZE thordata_importjob;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE 'thordata_%';

-- Vacuum for performance
VACUUM ANALYZE thordata_tradingdata;
```

### Backup Strategy
```bash
# Full database backup
pg_dump -h localhost -p 5433 -U thor_user -d thor_db > thor_backup.sql

# Table-specific backup
pg_dump -h localhost -p 5433 -U thor_user -d thor_db -t thordata_tradingdata > trading_data_backup.sql

# Compressed backup
pg_dump -h localhost -p 5433 -U thor_user -d thor_db | gzip > thor_backup.sql.gz
```

## Integration with 30+ App Platform

### API Endpoints (Future)
```python
# Suggested API structure
/api/trading-data/
├── GET /api/trading-data/                    # List with filtering
├── GET /api/trading-data/{id}/               # Single record
├── GET /api/trading-data/stats/              # Statistics
├── GET /api/trading-data/indicators/         # Available indicators
├── GET /api/trading-data/backtesting/        # Backtesting queries
└── POST /api/trading-data/bulk-query/        # Complex queries
```

### Performance Expectations
- **74K Records**: Sub-second queries with proper indexing
- **JSON Queries**: ~10-50ms for simple indicator lookups
- **Date Range Queries**: ~100-500ms for year-long ranges
- **Batch Inserts**: ~1000 records/second with current setup

## Troubleshooting

### Common Issues
1. **Slow JSON Queries**: Add GIN indexes on frequently queried JSON paths
2. **Import Failures**: Check CSV encoding and month name formats
3. **Memory Issues**: Reduce batch size in import command
4. **Connection Limits**: Monitor PostgreSQL connection pooling

### Monitoring Queries
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check table statistics
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE tablename LIKE 'thordata_%';

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename LIKE 'thordata_%';
```

## Version History
- **v1.0** (2025-09-21): Initial implementation with hybrid model
- **Future**: Real-time data integration, API endpoints, advanced analytics

---

**Note**: This system is designed to scale to millions of records and integrate with the larger 30+ app trading platform ecosystem.

**gets to the postgres terminal**
docker exec -it thor_postgres psql -U thor_user -d thor_db

**List all tables**
\dt

-- See the market open sessions table structure
\d+ "FutureTrading_marketopensession"

**View recent market open sessions**
SELECT id, session_number, country, total_signal, captured_at 
FROM "FutureTrading_marketopensession" 
ORDER BY captured_at DESC 
LIMIT 10;

**See all snapshots for the most recent Japan session**
SELECT symbol, last_price, change, change_percent, signal, weight
FROM "FutureTrading_futuresnapshot" 
WHERE session_id = (
    SELECT id FROM "FutureTrading_marketopensession" 
    WHERE country = 'Japan' 
    ORDER BY captured_at DESC 
    LIMIT 1
)
ORDER BY symbol;

-- Exit when done
\q