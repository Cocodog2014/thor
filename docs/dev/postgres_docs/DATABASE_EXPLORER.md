# PostgreSQL Database Explorer Commands

## Connect to PostgreSQL Database

### Using psql (PostgreSQL command line)
```bash
# Connect to the database
psql -h localhost -p 5433 -U thor_user -d thor_db

# You'll be prompted for password: thor_password
```

### Basic Database Exploration Commands

```sql
-- List all databases
\l

-- Connect to thor_db database
\c thor_db

-- List all tables
\dt

-- Describe a specific table structure
\d thordata_tradingdata
\d thordata_importjob

-- Show table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE 'thordata_%';

-- Show record counts
SELECT 
    'thordata_tradingdata' as table_name,
    COUNT(*) as record_count
FROM thordata_tradingdata
UNION ALL
SELECT 
    'thordata_importjob' as table_name,
    COUNT(*) as record_count
FROM thordata_importjob;

-- View first 5 trading records
SELECT 
    no_trades, 
    dlst, 
    year, 
    month, 
    date, 
    open_price, 
    close_price, 
    volume
FROM thordata_tradingdata 
ORDER BY no_trades DESC 
LIMIT 5;

-- View JSON data sample
SELECT 
    no_trades,
    dlst,
    jsonb_pretty(additional_data) 
FROM thordata_tradingdata 
LIMIT 1;

-- Check import jobs status
SELECT 
    file_name,
    status,
    processed_rows,
    total_rows,
    created_at,
    finished_at
FROM thordata_importjob
ORDER BY created_at DESC;

-- Exit psql
\q
```

## Alternative: Using pgAdmin (GUI Tool)
1. Download pgAdmin from: https://www.pgadmin.org/
2. Install and configure connection:
   - Host: localhost
   - Port: 5433
   - Database: thor_db
   - Username: thor_user
   - Password: thor_password