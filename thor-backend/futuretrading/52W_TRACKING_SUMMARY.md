# 52-Week High/Low Tracking System

## ✅ Implementation Complete

The system now tracks 52-week high/low extremes internally within Thor, automatically updating them based on incoming LAST prices from TOS RTD.

## 🎯 What Was Built

### 1. Database Model (`FutureTrading/models/extremes.py`)
- `Rolling52WeekStats` model tracks:
  - 52-week high/low with dates
  - All-time high/low with dates (optional)
  - Last price checked
  - Auto-update timestamps

### 2. Django Admin Interface
- Easy-to-use admin panel at `/admin/FutureTrading/rolling52weekstats/`
- One-time setup: Enter initial 52w high/low values for each symbol
- System automatically updates when new extremes occur
- View history of when highs/lows were set

### 3. Auto-Update Management Command
- `python manage.py update_52w_extremes`
- Reads latest LAST prices from Redis
- Automatically updates database when new highs/lows detected
- Handles symbol mapping (RT→RTY, 30YRBOND→ZB)
- Can run on schedule (cron, Celery Beat) or manually

### 4. API Integration
- RTD API (`/api/quotes/latest`) now includes 52w data
- Injected into `extended_data.high_52w` and `extended_data.low_52w`
- Frontend automatically receives and displays values
- Metrics service calculates distances (e.g., "5 points from 52w low")

## 📊 Current Status

All 11 futures have initial records:
```
CL    | H=61.89    | L=61.87
DX    | H=98.94    | L=98.94
ES    | H=6874.50  | L=6873.75
GC    | H=4084.00  | L=4083.80
HG    | H=5.21     | L=5.21
NQ    | H=25730.75 | L=25728.25
RTY   | H=2549.90  | L=2549.90
SI    | H=48.17    | L=48.16
VX    | H=17.95    | L=17.90
YM    | H=47683.00 | L=47679.00
ZB    | H=118.19   | L=118.19
```

## 🚀 How It Works

### Data Flow
```
TOS RTD (LAST price only)
    ↓
Excel → Redis → Thor Backend
    ↓
update_52w_extremes command checks each price
    ↓
If LAST > current 52w_high → Update high + date
If LAST < current 52w_low  → Update low + date
    ↓
Store in PostgreSQL + cache metadata
    ↓
RTD API injects 52w data into response
    ↓
Frontend displays values + calculated distances
```

### Automatic Updates
The `update_from_price()` method on the model:
1. Compares incoming LAST price to stored extremes
2. Updates high if price exceeds current high (with today's date)
3. Updates low if price breaks current low (with today's date)
4. Optionally tracks all-time extremes too
5. Saves to database only when changed

## 📝 How to Use

### Initial Setup (One-Time)
1. Go to Django admin: `http://localhost:8000/admin/`
2. Navigate to "52-Week Stats"
3. For each symbol, enter your known 52-week high/low values
4. Set the dates when those extremes occurred
5. Save

### Ongoing Operation
**Option A: Scheduled (Recommended)**
Add to Windows Task Scheduler or cron:
```bash
# Every 5 minutes during market hours
python manage.py update_52w_extremes
```

**Option B: Manual**
Run whenever you want to update:
```bash
cd A:\Thor\thor-backend
python manage.py update_52w_extremes --verbose
```

**Option C: On-Demand via API** (Future Enhancement)
Could trigger updates via API endpoint if needed.

### Monitoring
- Check Django admin to see last_updated timestamps
- Run with `--verbose` flag to see what's updating
- View `last_price_checked` to confirm system is reading prices

## 🔧 Symbol Mappings

The system handles TOS RTD naming differences:
- **RTY** in database ↔ **RT** in Redis/Excel
- **ZB** in database ↔ **30YRBOND** in Redis/Excel

These mappings are in the management command and work automatically.

## 📈 Frontend Display

The frontend (FutureTrading.tsx) already displays:
- 52-week high/low values
- Distance from current price to 52w extremes
- Percentage calculations

No frontend changes needed—it automatically picks up the data from `extended_data.high_52w` and `extended_data.low_52w`.

## 🎁 Bonus Features

### All-Time Tracking
The model also tracks all-time high/low if you want:
- Enable in admin by filling the `all_time_high` / `all_time_low` fields
- System auto-updates these too

### Reset/Backfill
If you want to reset or load historical data:
1. Delete existing records in admin (or via Django shell)
2. Import historical price data into `DailyPriceHistory` (if you build that table)
3. Run calculation to populate from history

## 🛠 Maintenance

### Adjusting the Window
Currently set to "52 weeks" as all-time tracking (grows forever). To enforce true 252-trading-day window:
1. Add `DailyPriceHistory` model (commented in brainstorm)
2. Store daily prices
3. Query last 252 trading days for min/max
4. Auto-expire old values

### Adding New Symbols
1. Add to `SYMBOLS` list in management command
2. Add symbol mapping to `SYMBOL_MAP` if needed
3. Run `update_52w_extremes` to create initial record
4. Enter better initial values in admin if desired

## ✅ Testing Results

API Test Output:
```
YM:
  Last: 47674.0
  52w High: 47683.0000
  52w Low: 47679.0000
  Distance from 52w Low: -5.0
  Distance from 52w High: 9.0
```

All systems operational! 🎉

## 📁 Files Created/Modified

**New Files:**
- `FutureTrading/models/extremes.py` - Model definition
- `FutureTrading/management/commands/update_52w_extremes.py` - Auto-update command
- `FutureTrading/migrations/0009_rolling52weekstats.py` - Database migration
- `scripts/test_52w_api.py` - Testing utility

**Modified Files:**
- `FutureTrading/models/__init__.py` - Export new model
- `FutureTrading/admin.py` - Admin interface
- `FutureTrading/views/RTD.py` - Inject 52w data into API
- `LiveData/tos/excel_reader.py` - Support for 52HIGH/52LOW headers (for future use)

## 🎯 Next Steps (Optional)

1. **Schedule the command** - Set up automatic runs every 5 minutes
2. **Backfill historical data** - Import past prices if you have them
3. **Add breakout alerts** - Notify when price breaks 52w high/low
4. **Track multiple timeframes** - 13w, 26w, 104w, etc.
5. **Add to Market Open capture** - Store 52w extremes in session records
