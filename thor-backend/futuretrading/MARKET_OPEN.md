# Market Open Capture & Grading - Implementation Plan

**Project:** Thor Futures Trading  
**Goal:** Capture market snapshots at regional opens, trade YM based on TOTAL composite, grade $100 target outcomes  
**Date:** October 26, 2025  
**Status:** Phase 1 - Models Built

---

## Progress Tracker

### ✅ Completed
- [x] Database schema design
- [x] MarketOpenSession model created
- [x] FutureSnapshot model created (replaces SymbolSnapshot)
- [x] Fields defined for all 11 futures + TOTAL composite
- [x] Entry price logic defined (Ask for BUY, Bid for SELL)
- [x] High/Low dynamic thresholds (±20 points = $100 target/stop)
- [x] Outcome tracking fields added
- [x] Register models in admin.py
- [x] Create and run migrations
- [x] Test models (all tests passed)
- [x] Auto-calculation of entry/target prices in model save()
- [x] Grading service built (checks every 0.5 seconds)
- [x] Management command created (grade_market_opens)

### 🔄 In Progress
- [ ] Build market open capture service (triggered by GlobalMarkets)

### 📋 To Do
- [ ] Build API endpoints for market open data
- [ ] Create frontend UI integration
- [ ] Add real-time updates via WebSocket/polling
- [ ] Build analytics/reporting views

---

## Frontend UI Plan

### **Integration with Global Markets (Split View)**

**Simple Layout Change (Frontend Only - No Backend Changes):**

Existing futures cards just need to be repositioned on the home page:

**Default State:**
- Home page shows Global Markets table (full width)

**When User Clicks "Future Trading" Icon:**
- Apply CSS grid layout: `grid-template-columns: 40% 60%`
- Left column: Global Markets table
- Right column: Existing futures cards component

**Implementation Notes:**
- ~50-100 lines of frontend code
- Just repositioning existing working components
- No API changes needed
- No backend changes needed

**Below Global Markets Table:**
Add section for captured market open sessions:
- Cards showing each session (time, market, signal, outcome)
- Expandable to show all 11 futures for that session
- Filters in slide-out drawer (date, market, signal, outcome)

**Real-Time Features:**
- Color-coded status badges:
  - 🟢 Green = WORKED
  - 🔴 Red = DIDN'T WORK
  - 🟡 Yellow = PENDING
  - ⚪ Gray = NEUTRAL
- Auto-refresh when outcomes change

---

## The Big Picture (What We're Building)

**When a market opens** (Japan, China, India, Europe, London, Pre-USA, USA):
1. **Capture** → Snapshot all 11 futures (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB) + TOTAL
2. **Decide** → Use TOTAL weighted average composite (BUY/SELL/HOLD)
3. **Trade YM Only** → Enter at Ask (BUY) or Bid (SELL), calculate $100 target/stop
4. **Grade** → Monitor price until target hit, stop hit, or window expires
5. **Store** → Record outcome for analytics (hit rates, EV, patterns by region/day)

**We track all 11 futures + TOTAL but only trade YM** — this builds data to discover which symbols' patterns predict YM success.

---

## Data Collection Summary

### MarketOpenSession (1 record per market open)
**Core Fields:**
- session_number, year, month, date, day, captured_at, country
- YM prices: open, close, ask, bid, last
- Entry prices: entry_price, high_dynamic (+20), low_dynamic (-20)
- Signal: bhs (BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL)
- Outcome: wndw (WORKED/DIDNT_WORK/NEUTRAL/PENDING), exit values

### FutureSnapshot (12 records per session: 11 futures + TOTAL)

**For Individual Futures (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB):**
1. Live price: last_price, change, change_percent
2. Bid/Ask: bid, bid_size, ask, ask_size
3. Market data: volume, vwap, spread
4. Session: open, close, open_vs_prev (number & percent)
5. 24h range: low_24h, high_24h, range_diff_24h, range_pct_24h
6. 52-week range: week_52_low, week_52_high, week_52_range_high_low, week_52_range_percent
7. Entry/targets: entry_price, high_dynamic (+20), low_dynamic (-20)

**For TOTAL Composite:**
1. weighted_average (e.g., -0.109)
2. signal (BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL)
3. weight (e.g., -3)
4. sum_weighted (e.g., 13.02)
5. instrument_count (11)
6. status (e.g., "LIVE TOTAL")

---

## PHASE 1: Backend Foundation (Models) ✅

### 1.1 Database Models - COMPLETED

#### **MarketOpenSession** ✅
Main session record with YM trade tracking and outcome grading.

#### **FutureSnapshot** ✅
Stores snapshot data for each of the 11 futures + TOTAL composite.
- Uses optional fields approach: TOTAL skips futures-specific fields, futures skip TOTAL-specific fields
- Enables flexible querying for back testing without data confusion

---

## PHASE 2: Capture Service (Next Up)

### Service Requirements:
1. Listen to GlobalMarkets for market open events
2. Fetch data from LiveData/Redis snapshot API
3. Calculate TOTAL composite signal
4. Create MarketOpenSession + 12 FutureSnapshots
5. Auto-calculate entry/target prices
6. Start grading service for monitoring

### API Endpoints Needed:
- `GET /api/futures/market-opens/` - List all sessions (with filters)
- `GET /api/futures/market-opens/{id}/` - Detail view with all 11 futures
- `GET /api/futures/market-opens/pending/` - Active/pending sessions
- `GET /api/futures/market-opens/stats/` - Analytics (win rates, etc.)
- `POST /api/futures/market-opens/capture/` - Manual trigger (testing)

### Frontend Routes:
- `/` - Home (Global Markets + Future Trading split view)
- `/futures/sessions` - Historical sessions table
- `/futures/analytics` - Analytics dashboard

---

## Technical Notes

### Data Flow:
```
TOS Excel RTD → LiveData → Redis → 
Market Open Capture → Database → 
Grading Service (0.5s loop) → 
Frontend (live updates)
```

### Key Files:
- Models: `FutureTrading/models/MarketOpen.py`
- Grading: `FutureTrading/services/market_open_grader.py`
- Admin: `FutureTrading/admin.py`
- Management: `FutureTrading/management/commands/grade_market_opens.py`

---

### 1.2 Capture Service (When Market Opens)

**Trigger:** Timezone app changes Market.status → "OPEN"

**Capture Flow:**
```python
1. Check if we already captured today for this region
   → If yes: ignore (idempotency)
   → If no: proceed

2. Call existing API: GET /api/futuretrading/quotes/latest
   → Returns TOTAL composite + all 11 symbols with bid/ask/signals

3. Extract YM data:
   → bid = 47,380
   → ask = 47,388
   → spread = 8
   → signal = "BUY" (from extended_data)

4. Determine entry (based on TOTAL composite, not YM's individual signal):
   If TOTAL = BUY/STRONG_BUY:
     → entry_price = YM ask (47,388)
     → target = entry + 20 ticks = 47,408
     → stop = entry - 20 ticks = 47,368
   
   If TOTAL = SELL/STRONG_SELL:
     → entry_price = YM bid (47,380)
     → target = entry - 20 ticks = 47,360
     → stop = entry + 20 ticks = 47,400
   
   If TOTAL = HOLD:
     → No entry, record session but outcome = "No Entry"

5. Store:
   → Create MarketOpenSession record
   → Create 11 SymbolSnapshot records (all futures)
   → Set outcome = "Pending" if entry made

6. If entry made:
   → Start grader loop (background task)
```

**Implementation:**
- Management command: `python manage.py listen_market_opens`
- OR Celery Beat task checking every 60 seconds
- OR Django signal if timezone app emits market_open event

---

### 1.3 Grading Loop (After Entry)

**Goal:** Monitor YM price until target/stop hit or window expires

**Frequency:**
- **FAST polling while Pending** → Every 1-5 seconds (until contract filled)
- **STOP polling after resolved** → No need to store data after outcome determined

**Grading Logic:**
```python
While session.outcome == "Pending":
    
    # Check if window expired
    elapsed = now - session.opened_at
    if elapsed > session.evaluation_window_sec:
        session.outcome = "Expired"
        session.pnl_usd = 0
        session.resolved_at = now
        STOP LOOP
        break
    
    # Get current YM bid price from LiveData
    current_bid = get_current_ym_price()  # /api/feed/quotes/snapshot?symbols=YM
    
    # Check if target or stop hit (first touch wins)
    if session.entry_side == "BUY":
        if current_bid >= session.target_price:
            session.outcome = "Worked"
            session.pnl_usd = 100
            session.resolved_at = now
            STOP LOOP
            break
        elif current_bid <= session.stop_price:
            session.outcome = "Didn't Work"
            session.pnl_usd = -100
            session.resolved_at = now
            STOP LOOP
            break
    
    elif session.entry_side == "SELL":
        if current_bid <= session.target_price:
            session.outcome = "Worked"
            session.pnl_usd = 100
            session.resolved_at = now
            STOP LOOP
            break
        elif current_bid >= session.stop_price:
            session.outcome = "Didn't Work"
            session.pnl_usd = -100
            session.resolved_at = now
            STOP LOOP
            break
    
    # Neither hit yet, sleep and check again
    time.sleep(5)  # or 1 second for faster resolution
```

**Key Points:**
- ✅ Poll FAST (every second) while outcome is Pending
- ✅ STOP LOOP immediately when outcome determined (target/stop/expired)
- ✅ No data storage needed after outcome — just update the session record once
- ✅ Use existing LiveData endpoint for current prices

**Implementation:**
- Celery task: `grade_session.delay(session_id)` triggered after capture
- OR background thread started from capture service
- OR management command: `python manage.py grade_pending_sessions` (runs continuously)

---

### 1.4 Phase 1 Deliverables

**Tables Created:**
- ✅ MarketOpenSession
- ✅ SymbolSnapshot
- ✅ SymbolConfig

**Services Working:**
- ✅ Capture service (listens for market open, stores snapshot)
- ✅ Grader loop (polls prices, updates outcome)
- ✅ Idempotency (one capture per region per day)

**Data Flow:**
```
Timezone "OPEN" → Capture snapshot → Store session + 11 snapshots
    ↓ (if entry made)
Start grader → Poll every 1-5 sec → Update outcome → Stop loop
```

**What We Can Do:**
- Capture market opens automatically
- Grade YM entries with $100 target/stop
- Store outcomes in database

**What We Can't Do Yet:**
- View captured data (no API endpoints)
- See analytics (no frontend)
- Export to Excel

---

## PHASE 2: Backend APIs (Read Captured Data)

**What We're Building:** REST endpoints to query sessions and analytics

### 2.1 Today View API

**Endpoint:** `GET /api/market-open/today`

**Returns:**
- All sessions captured today (across all regions)
- Per-session: region, time, composite, YM entry, outcome, P&L
- Summary: total sessions, hit rate, total P&L

**Example Response:**
```json
{
  "date": "2025-10-25",
  "sessions": [
    {
      "region": "Japan",
      "opened_at": "2025-10-25T09:00:00+09:00",
      "composite_signal": "BUY",
      "ym_entry": {
        "side": "BUY",
        "price": 47388.0,
        "target": 47408.0,
        "stop": 47368.0,
        "spread": 8.0
      },
      "outcome": "Worked",
      "pnl_usd": 100.0,
      "resolved_at": "2025-10-25T09:15:32+09:00"
    },
    // ... more regions
  ],
  "summary": {
    "total_sessions": 7,
    "worked": 4,
    "didnt_work": 2,
    "expired": 1,
    "total_pnl": 200.0,
    "hit_rate": 0.67
  }
}
```

---

### 2.2 History/Analytics API

**Endpoint:** `GET /api/market-open/history`

**Query Params:**
- `region` (filter by Japan, USA, etc.)
- `day_of_week` (filter by Monday, Tuesday, etc.)
- `start_date`, `end_date` (date range)
- `outcome` (filter by Worked, Didn't Work, etc.)

**Returns:**
- Filtered sessions
- Analytics: hit rate, expected value, avg resolution time
- Best performing region/day

**Example Response:**
```json
{
  "filters": {
    "region": "Japan",
    "day_of_week": "Monday",
    "start_date": "2025-10-01",
    "end_date": "2025-10-25"
  },
  "sessions": [ /* array of matching sessions */ ],
  "analytics": {
    "total_sessions": 4,
    "worked": 3,
    "didnt_work": 1,
    "hit_rate": 0.75,
    "expected_value": 50.0,  // (0.75 × 100) - (0.25 × 100)
    "avg_resolution_time_sec": 1024
  }
}
```

---

### 2.3 Symbol Detail API (Optional)

**Endpoint:** `GET /api/market-open/session/{session_id}/symbols`

**Returns:**
- All 11 SymbolSnapshot records for a specific session
- Shows what each symbol looked like at market open
- Useful for pattern analysis (e.g., "When ES shows Strong Buy, YM works 82% of time")

---

### 2.4 Phase 2 Deliverables

**APIs Created:**
- ✅ Today view endpoint
- ✅ History/analytics endpoint
- ✅ Symbol detail endpoint (optional)

**What We Can Do:**
- Query captured sessions via API
- Filter by region, day, date range
- Get analytics (hit rate, EV)

**What We Can't Do Yet:**
- See data in a nice UI (no frontend)

---

## PHASE 3: Frontend Dashboard

**What We're Building:** React pages to view and analyze sessions

### 3.1 Today View Page

**Route:** `/futures/market-open/today`

**Components:**
- **Header:** Date, total sessions, total P&L
- **Session Cards:** One card per region opened today
  - Region name + time opened
  - Composite signal badge (green=BUY, red=SELL, gray=HOLD)
  - YM entry details (price, spread, target/stop)
  - Outcome badge (green=Worked, red=Didn't, gray=Expired)
  - P&L (+$100, -$100, $0)
  - Expandable: show all 11 symbols' snapshots
- **Summary Bar:** Hit rate, total P&L, best region today

**Auto-refresh:** Every 30 seconds (while grading is pending)

---

### 3.2 History/Analytics Page

**Route:** `/futures/market-open/history`

**Components:**
- **Filters Panel:**
  - Region dropdown (All, Japan, China, etc.)
  - Day of week checkboxes
  - Date range picker
  - Outcome filter (All, Worked, Didn't, Expired)

- **Analytics Cards:**
  - Hit rate by region (bar chart)
  - Hit rate by day of week (bar chart)
  - Expected value table
  - Best performing region/day

- **Session Table:**
  - Sortable columns: region, date, composite, outcome, P&L
  - Click row → expand to show 11 symbols

---

### 3.3 Phase 3 Deliverables

**Pages Created:**
- ✅ Today view (current day sessions)
- ✅ History view (filtered analytics)

**What We Can Do:**
- See all market open captures in UI
- Filter by region, day, date range
- Analyze hit rates and expected value
- Export data (optional: CSV download)

**We're Done!** 🎉

---

## Data Storage Strategy

### What We Store:

**At Market Open (One-time):**
- ✅ MarketOpenSession record (1 per region per day)
- ✅ 11 SymbolSnapshot records (all futures at open)
- ✅ Total: ~12 database rows per capture

**During Grading (Fast polling):**
- ❌ **NO intermediate price data stored**
- ❌ **NO tick-by-tick history**
- ✅ **ONLY the final outcome** (Worked/Didn't/Expired) stored in session record

**After Outcome Resolved:**
- ❌ **STOP polling** immediately
- ✅ Session record updated with outcome, P&L, timestamp
- ✅ No further storage needed

### Polling Frequency:

**Phase 1 (Simple):**
- Every **1-5 seconds** while outcome = "Pending"
- Call: `GET /api/feed/quotes/snapshot?symbols=YM` (lightweight)
- Check: Did bid hit target or stop?
- Update: If yes, save outcome and STOP LOOP

**Phase 2 (Later - Redis Streaming):**
- Subscribe to `live_data:quotes:YM` Redis channel
- Get tick updates in real-time (sub-second)
- No polling needed, instant resolution

### Why This Works:

✅ **Minimal storage** — only capture + outcome, no intermediate ticks  
✅ **Fast resolution** — 1-5 second polls catch target/stop quickly  
✅ **No waste** — stop polling after outcome determined  
✅ **Scalable** — 7 regions × 250 days = ~1,750 sessions/year (tiny)

---

## Quick Reference Tables

### Symbols & Tick Values

| Symbol | Tick Size | Tick Value | $100 = X Ticks | Contract |
|--------|-----------|------------|----------------|----------|
| **YM** | 1.0 | $5.00 | 20 | Dow Mini |
| ES | 0.25 | $12.50 | 8 | S&P 500 |
| NQ | 0.25 | $5.00 | 20 | Nasdaq |
| RTY | 0.10 | $5.00 | 20 | Russell |
| CL | 0.01 | $10.00 | 10 | Crude Oil |
| SI | 0.005 | $25.00 | 4 | Silver |
| HG | 0.0005 | $12.50 | 8 | Copper |
| GC | 0.10 | $10.00 | 10 | Gold |
| VX | 0.05 | $50.00 | 2 | VIX |
| DX | 0.005 | $5.00 | 20 | Dollar |
| ZB | 0.03125 | $31.25 | ~3.2 | 30Y Bond |

### Regions Tracked

1. **Japan** (Tokyo) - Asia/Tokyo
2. **China** (Shanghai) - Asia/Shanghai
3. **India** (Bombay) - Asia/Kolkata
4. **EuroNext** (Amsterdam) - Europe/Amsterdam
5. **London** - Europe/London
6. **Pre_USA** - America/New_York (pre-market)
7. **USA** - America/New_York (regular)

### TOTAL Composite Thresholds

- `signal_weight_sum > 9` → **STRONG_BUY**
- `3 < sum ≤ 9` → **BUY**
- `-3 ≤ sum ≤ 3` → **HOLD**
- `-9 ≤ sum < -3` → **SELL**
- `sum < -9` → **STRONG_SELL**

### Outcome States

- **Pending** → Grading in progress
- **Worked** → Target hit (+$100)
- **Didn't Work** → Stop hit (-$100)
- **Expired** → Window closed, neither hit ($0)
- **No Entry** → TOTAL was HOLD, no trade made
- **Error** → Technical failure during grading

---

## Implementation Checklist

### Phase 1: Backend Foundation
- [ ] Create Django models (MarketOpenSession, SymbolSnapshot, SymbolConfig)
- [ ] Write migrations and apply
- [ ] Seed SymbolConfig table with 11 symbols
- [ ] Create capture service (fetch snapshot, store session)
- [ ] Create grader service (poll prices, update outcome)
- [ ] Wire up timezone listener (management command or Celery)
- [ ] Test: Capture one manual session, verify grading works

### Phase 2: Backend APIs
- [ ] Create `/api/market-open/today` endpoint
- [ ] Create `/api/market-open/history` endpoint
- [ ] Add filters (region, day, date range)
- [ ] Add analytics calculations (hit rate, EV)
- [ ] Test: Query API, verify data correct

### Phase 3: Frontend
- [ ] Create Today view page (`/futures/market-open/today`)
- [ ] Create History view page (`/futures/market-open/history`)
- [ ] Add charts (hit rate by region/day)
- [ ] Add filters UI
- [ ] Add auto-refresh (30 sec while pending)
- [ ] Test: View sessions, verify UI matches API

---

## Questions to Resolve Before Coding

1. **Tick values** — Verify table above is correct (especially ZB's 1/32 tick)
2. **Polling speed** — 1 second, 5 seconds, or faster? (determines resolution accuracy)
3. **Evaluation window** — Default 30 minutes OK? Different per region?
4. **App structure** — New Django app `MarketOpenCapture` or extend `FutureTrading`?
5. **Background tasks** — Celery (recommended), Django-Q, or simple threading?
6. **Timezone listener** — Polling, signals, or Celery Beat?

---

## Success = Can Answer These Questions

✅ **"What was my hit rate for Japan on Mondays?"**  
✅ **"Which region has the best expected value?"**  
✅ **"Does ES Strong Buy signal predict YM success?"**  
✅ **"How much P&L did I make this week?"**  
✅ **"What was the composite signal when London opened today?"**

---

## Timeline Estimate

- **Phase 1 (Backend):** 3-5 days
- **Phase 2 (APIs):** 1-2 days
- **Phase 3 (Frontend):** 2-3 days
- **Testing/Fixes:** 1-2 days

**Total: 7-12 days** (full-time work)

---

**Status:** ✅ Brainstorm complete, ready for your approval  
**Next:** You confirm approach, I start building Phase 1

---

**Status:** ✅ Brainstorm complete, ready for your approval  
**Next:** You confirm approach, I start building Phase 1

**Trade:** Only **YM** (Dow Jones E-mini futures)  
**Track:** All 11 futures (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB)  
**Purpose:** Build analytics to discover if other futures' patterns predict YM outcomes better on certain days/regions.

### Q2: TOTAL Composite Calculation ✅ CONFIRMED
**Source:** Existing `FutureTrading` app already computes this  
**Location:** `thor-backend/FutureTrading/services/classification.py` → `compute_composite()`  
**Formula:**
```python
# Each symbol gets HBS classification (Strong Buy/Buy/Hold/Sell/Strong Sell)
# Each classification has signal weight: +2, +1, 0, -1, -2
# Bear market instruments (VX, DX, GC, ZB) have inverted weights
# Sum all signal weights = signal_weight_sum

if signal_weight_sum > 9:
    composite_signal = "STRONG_BUY"
elif 3 < signal_weight_sum <= 9:
    composite_signal = "BUY"
elif -3 <= signal_weight_sum <= 3:
    composite_signal = "HOLD"
elif -9 <= signal_weight_sum < -3:
    composite_signal = "SELL"
elif signal_weight_sum < -9:
    composite_signal = "STRONG_SELL"
```

**Current API Endpoint:** `GET /api/futuretrading/quotes/latest`  
**Response includes:**
- `rows[]` - Array of 11 instruments with bid/ask/last/signal/weights
- `total.composite_signal` - Overall market direction (BUY/SELL/HOLD)
- `total.signal_weight_sum` - Numeric sum used for classification

### Q3: Entry Logic ✅ CONFIRMED
**For YM Only:**
- `TOTAL = STRONG_BUY` or `BUY` → Enter at **YM Ask** (market taker, pay the spread)
- `TOTAL = STRONG_SELL` or `SELL` → Enter at **YM Bid** (market taker, receive the spread)
- `TOTAL = HOLD` → **No trade**, record session but mark as "No Entry"

**Why Ask/Bid?** We're simulating immediate execution (market order), not limit orders.

### Q4: Tick Values & Target Calculation ✅ REFERENCE TABLE CREATED

| Symbol | Tick Size | Tick Value (USD) | $100 Target (Ticks) | Contract Size | Notes |
|--------|-----------|------------------|---------------------|---------------|-------|
| **YM** | 1 | $5.00 | 20 | $5 × index | Dow Jones E-mini |
| ES | 0.25 | $12.50 | 8 | $50 × index | S&P 500 E-mini |
| NQ | 0.25 | $5.00 | 20 | $20 × index | Nasdaq 100 |
| RTY | 0.10 | $5.00 | 20 | $50 × index | Russell 2000 |
| CL | 0.01 | $10.00 | 10 | 1,000 barrels | Crude Oil |
| SI | 0.005 | $25.00 | 4 | 5,000 oz | Silver |
| HG | 0.0005 | $12.50 | 8 | 25,000 lbs | Copper |
| GC | 0.10 | $10.00 | 10 | 100 oz | Gold |
| VX | 0.05 | $50.00 | 2 | $1,000 × index | VIX Futures |
| DX | 0.005 | $5.00 | 20 | $1,000 × index | Dollar Index |
| ZB | 1/32 (0.03125) | $31.25 | ~3.2 | $100,000 face | 30-Yr Bond |

**Source:** Excel dashboard shows "Qty × Tick 1 = $X" confirming tick values  
**Confirmation Needed:** User should verify these match actual contract specs

### Q5: Grading Window ✅ DEFAULT SET
**Initial:** 30 minutes (1,800 seconds) from market open  
**Configurable:** Can be adjusted per region or globally  
**Future Enhancement:** Real-time tick-driven resolution via Redis streaming

### Q6: Data Sources ✅ MAPPED

**LiveData/TOS Integration:**
- **Excel File:** `A:\Thor\CleanData.xlsm`
- **Sheet:** `Futures`
- **Range:** `A1:N12` (headers + 11 instruments)
- **API Endpoint:** `GET /api/feed/tos/quotes/latest/?consumer=futures_trading`
- **Response Format:**
```json
{
  "quotes": [
    {
      "symbol": "YM",
      "bid": 47380.0,
      "ask": 47388.0,
      "last": 47387.0,
      "bid_size": 2,
      "ask_size": 2,
      "volume": 87927,
      "open": 46874.0,
      "high": 47506.0,
      "low": 47396.0,
      "close": 47396.0,
      "change": -522.0,
      "spread": 8.0
    },
    // ... 10 more symbols
  ],
  "count": 11,
  "source": "TOS_RTD_Excel"
}
```

**Enrichment Pipeline:**
1. Raw TOS data → `LiveData/tos/views.py::get_latest_quotes()`
2. Enriched with signals → `FutureTrading/views.py::LatestQuotesView`
3. Returns composite + per-symbol classification

### Q7: Timezone App Integration ✅ CONFIRMED

**Models:** `thor-backend/timezones/models.py`

**Market Model Fields:**
- `country` (e.g., "Japan", "China", "United Kingdom")
- `timezone_name` (e.g., "Asia/Tokyo", "Europe/London")
- `market_open_time`, `market_close_time` (local times)
- `status` → **"OPEN"** or **"CLOSED"** (this is our trigger!)
- `is_active` (enable/disable tracking)

**Display Names (User's Excel Regions):**
- Japan → Tokyo
- China → Shanghai
- India → Bombay
- Netherlands → Amsterdam
- United Kingdom → London
- Pre_USA → Pre_USA
- USA → USA

**Holiday/Weekend Handling:** ✅ Already built-in
- Timezone app tracks `USMarketStatus.is_us_market_open_today()`
- Respects market holidays
- Won't trigger captures on closed days

**API Endpoint:** `GET /api/timezones/markets/`
- Returns list of markets with current status
- Includes `status: "OPEN"` or `status: "CLOSED"`

**Event Detection Options:**
1. **Polling:** Check timezone API every 60 seconds for status changes
2. **Django Signals:** Market model emits signal on `status` change (requires management command/scheduler)
3. **Celery Beat:** Scheduled task checks markets and triggers capture

---

## Phase 1: Specification (1-Pager)

### Symbols to Track (All 11)
YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB

### Regions to Monitor (7 Main Markets)
- **Japan** (Tokyo) - Asia/Tokyo
- **China** (Shanghai) - Asia/Shanghai
- **India** (Bombay) - Asia/Kolkata
- **EuroNext** (Amsterdam) - Europe/Amsterdam
- **London** (United Kingdom) - Europe/London
- **Pre_USA** - America/New_York (pre-market hours)
- **USA** - America/New_York (regular hours)

### Trigger Source
**Timezone App Status Change:** `Market.status` → "OPEN"

### Entry Policy (YM Only)
- **Composite = BUY/STRONG_BUY** → Enter YM at **Ask**
- **Composite = SELL/STRONG_SELL** → Enter YM at **Bid**
- **Composite = HOLD** → No entry (record but don't grade)

### Profit Target
**Fixed:** `take_profit_usd = $100` per contract

### Stop Loss
**Fixed:** `stop_loss_usd = $100` per contract (symmetrical)

### Target Calculation (YM Specific)
```python
ym_tick_value = 5.00  # dollars per tick
target_ticks = 100 / 5.00 = 20 ticks

# Example: BUY at Ask = 47,388
target_price = 47,388 + 20 = 47,408  (profit if bid hits this)
stop_price = 47,388 - 20 = 47,368    (loss if bid hits this)
```

### Evaluation Window
**Default:** 30 minutes (1,800 seconds)  
**Configurable:** Per region or globally via config table

### First Touch Rule
Whichever hits first (target or stop) determines the outcome:
- **Target hit first** → `Worked` (+$100)
- **Stop hit first** → `Didn't Work` (-$100)
- **Neither within window** → `Expired` ($0)

### Grading Data Source (Initial)
**Polling LiveData:** Check YM bid price every 5-10 seconds  
**Future:** Redis streaming for tick-level resolution

---

## Phase 2: Data Flow & Event Pipeline

### Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  TRIGGER: Timezone App → Market.status changes to "OPEN"       │
│  Payload: { region: "Japan", status: "OPEN", timestamp }       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  IDEMPOTENCY CHECK                                              │
│  Query: MarketOpenSession exists for (region, today)?          │
│  - If YES → Ignore duplicate, log and exit                     │
│  - If NO → Proceed to capture                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPTURE SNAPSHOT                                               │
│  Call: GET /api/futuretrading/quotes/latest                    │
│  Returns:                                                       │
│    - rows[11]: Each symbol's bid/ask/last/signal/weight        │
│    - total.composite_signal: BUY/SELL/HOLD                     │
│    - total.signal_weight_sum: numeric composite score          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  CALCULATE YM ENTRY                                             │
│  Extract YM row from snapshot:                                 │
│    ym_bid = 47,380                                              │
│    ym_ask = 47,388                                              │
│    ym_spread = 8                                                │
│                                                                 │
│  If composite = BUY/STRONG_BUY:                                 │
│    entry_price = ym_ask (47,388)                                │
│    target = entry + 20 ticks = 47,408                           │
│    stop = entry - 20 ticks = 47,368                             │
│                                                                 │
│  If composite = SELL/STRONG_SELL:                               │
│    entry_price = ym_bid (47,380)                                │
│    target = entry - 20 ticks = 47,360                           │
│    stop = entry + 20 ticks = 47,400                             │
│                                                                 │
│  If composite = HOLD:                                           │
│    entry_price = None (no trade)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STORE SESSION & SNAPSHOTS                                      │
│  Create:                                                        │
│    1. MarketOpenSession (one record)                            │
│       - region, opened_at, composite, YM entry details          │
│       - ym_outcome = "Pending"                                  │
│                                                                 │
│    2. SymbolSnapshot (11 records, one per future)               │
│       - Each symbol's bid/ask/last/signal/weight at open        │
│       - Theoretical entry prices (for analytics)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCHEDULE GRADER (if entry was made)                            │
│  Background task / Celery:                                      │
│    - Poll YM price every 5-10 seconds                           │
│    - Check if target or stop hit                                │
│    - Update session.ym_outcome when resolved                    │
│    - Stop after window expires or outcome determined            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  ANALYTICS READY                                                │
│  Query:                                                         │
│    - Sessions by region, day_of_week, outcome                   │
│    - Hit rates: % Worked, % Didn't Work, % Expired             │
│    - Expected value: (Worked% × $100) - (Didn't% × $100)       │
│    - Correlations: Do certain symbols' signals predict better?  │
└─────────────────────────────────────────────────────────────────┘
```

### Example Payloads

#### Timezone Event (Trigger)
```json
{
  "event": "market_open",
  "market": {
    "country": "Japan",
    "display_name": "Tokyo",
    "timezone": "Asia/Tokyo",
    "status": "OPEN",
    "opened_at": "2025-10-25T09:00:00+09:00"
  }
}
```

#### FutureTrading Snapshot (Capture)
```json
{
  "rows": [
    {
      "instrument": {
        "symbol": "YM",
        "name": "Dow Jones E-mini",
        "tick_size": 1.0,
        "display_precision": 2
      },
      "bid": 47380.0,
      "ask": 47388.0,
      "last": 47387.0,
      "bid_size": 2,
      "ask_size": 2,
      "spread": 8.0,
      "volume": 87927,
      "open_price": 46874.0,
      "high_price": 47506.0,
      "low_price": 47396.0,
      "close_price": 47396.0,
      "change": -522.0,
      "extended_data": {
        "signal": "BUY",
        "stat_value": 10.0,
        "contract_weight": 1.0,
        "signal_weight": 1
      }
    }
    // ... 10 more symbols
  ],
  "total": {
    "sum_weighted": 125.5,
    "avg_weighted": 11.409,
    "count": 11,
    "signal_weight_sum": 5,
    "composite_signal": "BUY",
    "composite_signal_weight": 1,
    "as_of": "2025-10-25T09:00:00+09:00"
  }
}
```

#### MarketOpenSession Record (Storage)
```json
{
  "session_id": "uuid-123",
  "region": "Japan",
  "opened_at": "2025-10-25T09:00:00+09:00",
  "date": "2025-10-25",
  "day_of_week": "Saturday",
  "bhs": "BUY",
  "weight": 5,
  "weighted_average": 11.409,
  "ym_entry_side": "BUY",
  "ym_entry_price": 47388.0,
  "ym_bid_at_open": 47380.0,
  "ym_ask_at_open": 47388.0,
  "ym_last_at_open": 47387.0,
  "ym_spread_at_open": 8.0,
  "ym_target_price": 47408.0,
  "ym_stop_price": 47368.0,
  "ym_outcome": "Pending",
  "ym_pnl_usd": null,
  "ym_resolved_at": null,
  "evaluation_window_sec": 1800,
  "created_at": "2025-10-25T09:00:05+09:00"
}
```

#### SymbolSnapshot Record (Tracking)
```json
{
  "snapshot_id": "uuid-456",
  "session_id": "uuid-123",
  "symbol": "ES",
  "captured_at": "2025-10-25T09:00:00+09:00",
  "bid": 6824.75,
  "ask": 6825.50,
  "last": 6825.25,
  "spread": 0.75,
  "volume": 1203709,
  "open": 6825.25,
  "high": 6826.25,
  "low": 6824.25,
  "close": 6825.25,
  "change": 50.25,
  "hbs_classification": "Strong Buy",
  "hbs_weight": 2,
  "tick_size": 0.25,
  "tick_value_usd": 12.50,
  "theoretical_entry_side": "BUY",
  "theoretical_entry_price": 6825.50,
  "theoretical_target_price": 6827.50,
  "theoretical_stop_price": 6823.50
}
```

#### Grading Update (Outcome)
```json
{
  "session_id": "uuid-123",
  "ym_outcome": "Worked",
  "ym_pnl_usd": 100.0,
  "ym_resolved_at": "2025-10-25T09:15:32+09:00",
  "resolution_price": 47408.5,
  "resolution_reason": "Target hit at 09:15:32"
}
```

---

## Phase 3: Configuration & Reference Data

### Symbol Reference Config Table

**Database Table:** `FutureTrading_SymbolConfig` (new)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| symbol | CharField(10) | Trading symbol | "YM" |
| tick_size | DecimalField | Minimum price increment | 1.0 |
| tick_value_usd | DecimalField | Dollar value per tick | 5.00 |
| take_profit_usd | DecimalField | Profit target per contract | 100.00 |
| stop_loss_usd | DecimalField | Stop loss per contract | 100.00 |
| display_precision | IntegerField | Decimal places for UI | 2 |
| contract_size | CharField | Descriptive contract size | "$5 × index" |
| is_active | BooleanField | Enable capture/grading | True |
| created_at | DateTimeField | Record creation | auto |
| updated_at | DateTimeField | Last modified | auto |

**Initial Data (Seed Script):**
```python
# Management command: python manage.py seed_symbol_config

SYMBOL_CONFIG = [
    {"symbol": "YM", "tick_size": 1.0, "tick_value_usd": 5.00, "display_precision": 2},
    {"symbol": "ES", "tick_size": 0.25, "tick_value_usd": 12.50, "display_precision": 2},
    {"symbol": "NQ", "tick_size": 0.25, "tick_value_usd": 5.00, "display_precision": 2},
    {"symbol": "RTY", "tick_size": 0.10, "tick_value_usd": 5.00, "display_precision": 2},
    {"symbol": "CL", "tick_size": 0.01, "tick_value_usd": 10.00, "display_precision": 2},
    {"symbol": "SI", "tick_size": 0.005, "tick_value_usd": 25.00, "display_precision": 3},
    {"symbol": "HG", "tick_size": 0.0005, "tick_value_usd": 12.50, "display_precision": 4},
    {"symbol": "GC", "tick_size": 0.10, "tick_value_usd": 10.00, "display_precision": 2},
    {"symbol": "VX", "tick_size": 0.05, "tick_value_usd": 50.00, "display_precision": 2},
    {"symbol": "DX", "tick_size": 0.005, "tick_value_usd": 5.00, "display_precision": 3},
    {"symbol": "ZB", "tick_size": 0.03125, "tick_value_usd": 31.25, "display_precision": 5},
]
```

### Global Settings Config Table

**Database Table:** `FutureTrading_GlobalConfig` (new)

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| config_key | CharField(50) | Setting identifier | "default_evaluation_window_sec" |
| config_value | TextField | JSON-encoded value | "1800" |
| description | TextField | Human-readable description | "Default grading window in seconds" |
| is_active | BooleanField | Enable setting | True |
| updated_at | DateTimeField | Last modified | auto |

**Initial Settings:**
```python
GLOBAL_CONFIG = [
    {
        "key": "default_evaluation_window_sec",
        "value": "1800",
        "description": "Default grading window (30 minutes)"
    },
    {
        "key": "grader_poll_interval_sec",
        "value": "5",
        "description": "How often to check prices during grading"
    },
    {
        "key": "capture_enabled",
        "value": "true",
        "description": "Master switch for market open captures"
    },
    {
        "key": "grading_enabled",
        "value": "true",
        "description": "Master switch for outcome grading"
    }
]
```

### Per-Region Overrides (Optional)

**Database Table:** `FutureTrading_RegionConfig` (new)

| Field | Type | Description |
|-------|------|-------------|
| region | CharField(50) | Region name (matches timezone Market.country) |
| evaluation_window_sec | IntegerField | Region-specific window override |
| is_active | BooleanField | Enable captures for this region |
| notes | TextField | Admin notes |

**Example:**
```python
# Pre_USA might need longer window due to low liquidity
{"region": "Pre_USA", "evaluation_window_sec": 3600}  # 60 minutes

# USA regular hours might be faster
{"region": "USA", "evaluation_window_sec": 1200}  # 20 minutes
```

---

## Phase 4: Operational Behaviors

### Idempotency at Market Open

**Problem:** Timezone app might send multiple "OPEN" status updates for same day  
**Solution:** Check before capture

```python
def should_capture(region: str, timestamp: datetime) -> bool:
    """Check if we've already captured for this region today."""
    today = timestamp.date()
    existing = MarketOpenSession.objects.filter(
        region=region,
        date=today
    ).exists()
    
    if existing:
        logger.info(f"Duplicate open event for {region} on {today} - ignoring")
        return False
    
    return True
```

### Resilience & Error Handling

**Snapshot Fails:**
1. Retry up to 3 times with 2-second delay
2. If still failing, create a "Missed Capture" event record
3. Log detailed error for investigation
4. Send alert (optional: email/Slack webhook)

**Grader Fails:**
1. If price polling fails, retry briefly
2. If persistent failure, mark outcome as "Error"
3. Store partial data (entry recorded, grading incomplete)

**Example Code Pattern:**
```python
def capture_snapshot_with_retry(region: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            snapshot = fetch_futuretrading_quotes()
            return snapshot
        except Exception as e:
            logger.warning(f"Capture attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                # Final failure - record it
                MissedCapture.objects.create(
                    region=region,
                    error=str(e),
                    timestamp=timezone.now()
                )
                raise
```

### Grader Scheduling Options

**Option 1: Celery Beat + Task Queue (Recommended)**
```python
# Capture triggers a delayed task
from celery import shared_task

@shared_task
def grade_market_session(session_id: str):
    """Poll prices and grade outcome for a session."""
    session = MarketOpenSession.objects.get(id=session_id)
    
    start_time = session.opened_at
    window_sec = session.evaluation_window_sec
    poll_interval = 5  # seconds
    
    while True:
        elapsed = (timezone.now() - start_time).total_seconds()
        
        if elapsed > window_sec:
            # Window expired
            session.ym_outcome = "Expired"
            session.ym_pnl_usd = 0
            session.ym_resolved_at = timezone.now()
            session.save()
            break
        
        # Check current price
        current_price = get_current_ym_price()
        outcome = check_target_or_stop_hit(session, current_price)
        
        if outcome:
            # Target or stop hit
            session.ym_outcome = outcome  # "Worked" or "Didn't Work"
            session.ym_pnl_usd = 100 if outcome == "Worked" else -100
            session.ym_resolved_at = timezone.now()
            session.save()
            break
        
        time.sleep(poll_interval)
```

**Option 2: Django Management Command + Cron**
```bash
# Run every minute
* * * * * cd /path/to/thor-backend && python manage.py grade_pending_sessions
```

**Option 3: Background Thread (Simple, for MVP)**
```python
import threading

def start_grader_thread(session_id: str):
    thread = threading.Thread(target=grade_market_session, args=(session_id,))
    thread.daemon = True
    thread.start()
```

### Auditability

**Every capture includes:**
- Exact timestamp of capture (timezone-aware)
- Raw prices used: bid, ask, last, spread
- Composite signal and numeric score
- Entry price determination logic
- All 11 symbols' data at that moment

**Grading trail includes:**
- Resolution timestamp
- Resolution price (bid value when target/stop hit)
- Resolution reason ("Target hit", "Stop hit", "Window expired")
- Time elapsed from entry to resolution

**Query Examples:**
```python
# All captures today
sessions_today = MarketOpenSession.objects.filter(date=date.today())

# Hit rate for Japan region, Mondays
from datetime import timedelta
monday_sessions = MarketOpenSession.objects.filter(
    region="Japan",
    date__week_day=2  # Monday in Django
)
hit_rate = monday_sessions.filter(ym_outcome="Worked").count() / monday_sessions.count()

# Expected value calculation
worked = monday_sessions.filter(ym_outcome="Worked").count()
didnt_work = monday_sessions.filter(ym_outcome="Didn't Work").count()
total = monday_sessions.count()
ev = (worked / total * 100) - (didnt_work / total * 100)
print(f"Japan Mondays EV: ${ev:.2f} per contract")
```

---

## Phase 5: Outputs & Dashboards

### Today View (Primary UI)

**Endpoint:** `GET /api/futuretrading/market-open/today`

**Response:**
```json
{
  "date": "2025-10-25",
  "sessions": [
    {
      "region": "Japan",
      "opened_at": "2025-10-25T09:00:00+09:00",
      "composite": "BUY",
      "ym_entry": {
        "side": "BUY",
        "price": 47388.0,
        "target": 47408.0,
        "stop": 47368.0,
        "spread_at_entry": 8.0
      },
      "outcome": "Worked",
      "pnl": 100.0,
      "resolved_at": "2025-10-25T09:15:32+09:00",
      "elapsed_sec": 932,
      "symbols": [
        {"symbol": "YM", "signal": "BUY", "bid": 47380, "ask": 47388},
        {"symbol": "ES", "signal": "Strong Buy", "bid": 6824.75, "ask": 6825.50},
        // ... 9 more
      ]
    },
    {
      "region": "China",
      "opened_at": "2025-10-25T10:30:00+08:00",
      "composite": "HOLD",
      "ym_entry": null,
      "outcome": "No Entry",
      "pnl": 0,
      "symbols": [...]
    }
    // ... more regions
  ],
  "summary": {
    "total_sessions": 7,
    "entries_made": 5,
    "worked": 3,
    "didnt_work": 1,
    "expired": 1,
    "total_pnl": 200.0,
    "hit_rate": 0.75
  }
}
```

**UI Components:**
- Card per region with outcome badge (green=Worked, red=Didn't, gray=Expired/No Entry)
- YM entry details: price, spread, target/stop levels
- Per-symbol snapshot table (collapsible)
- Summary metrics bar at top

### History View (Analytics)

**Endpoint:** `GET /api/futuretrading/market-open/history`

**Query Params:**
- `region` (filter: Japan, China, etc.)
- `day_of_week` (filter: Mon, Tue, ...)
- `start_date`, `end_date` (date range)
- `outcome` (filter: Worked, Didn't Work, Expired)

**Response:**
```json
{
  "filters": {
    "region": "Japan",
    "day_of_week": "Monday",
    "start_date": "2025-10-01",
    "end_date": "2025-10-25"
  },
  "sessions": [
    // List of matching sessions
  ],
  "analytics": {
    "total_sessions": 20,
    "entries_made": 18,
    "worked": 12,
    "didnt_work": 5,
    "expired": 1,
    "hit_rate": 0.67,
    "expected_value_per_contract": 38.89,
    "avg_resolution_time_sec": 1024,
    "best_region": "USA",
    "best_day": "Wednesday"
  },
  "correlation_insights": [
    {
      "symbol": "ES",
      "signal": "Strong Buy",
      "ym_worked_rate": 0.82,
      "sample_size": 15
    },
    // More insights
  ]
}
```

**UI Components:**
- Filters panel (region, day, date range)
- Hit rate chart (bar chart by region/day)
- Expected value table
- Correlation matrix (which symbol signals predict YM success)
- Session list with sortable columns

### Real-Time View (Future Enhancement)

**Endpoint:** WebSocket `/ws/futuretrading/market-open/live`

**Messages:**
- New session opened
- Outcome resolved
- Price updates during grading window

---

## Phase 6: Validation & UAT

### Acceptance Test Checklist

#### Price Sanity Checks
- [ ] Ask ≥ Bid for all symbols in capture
- [ ] Entry price matches entry side (Ask for BUY, Bid for SELL)
- [ ] Spread = Ask - Bid (non-negative)
- [ ] Tick sizes match reference config

#### Target Math Validation
- [ ] `target_ticks = take_profit_usd / tick_value_usd` is integer or near-integer
- [ ] For YM: 100 / 5.00 = 20 ticks exactly
- [ ] Target price = entry ± (target_ticks × tick_size)
- [ ] Stop price = entry ∓ (target_ticks × tick_size)

#### Outcome Logic Tests
- [ ] When price crosses target first → outcome = "Worked"
- [ ] When price crosses stop first → outcome = "Didn't Work"
- [ ] When window expires with no cross → outcome = "Expired"
- [ ] P&L correct: Worked = +$100, Didn't = -$100, Expired = $0

#### Composite Signal Tests
- [ ] Signal weight sum > 9 → STRONG_BUY
- [ ] Signal weight sum 3-9 → BUY
- [ ] Signal weight sum -3 to +3 → HOLD
- [ ] Signal weight sum -9 to -3 → SELL
- [ ] Signal weight sum < -9 → STRONG_SELL
- [ ] Bear market instruments (VX, DX, GC, ZB) have inverted weights

#### Idempotency Tests
- [ ] Second capture request for same region/day is ignored
- [ ] "Duplicate open event" logged but no error thrown
- [ ] No duplicate session records in database

#### Timezone & Holiday Tests
- [ ] Captures only happen when Market.status = "OPEN"
- [ ] No captures on weekends (unless market actually open)
- [ ] No captures on holidays (timezone app handles this)
- [ ] Timestamps are timezone-aware and correct

#### Error Handling Tests
- [ ] Snapshot fetch failure → retry 3 times → create MissedCapture record
- [ ] Grader price fetch failure → retry briefly → mark as "Error"
- [ ] Invalid data (missing bid/ask) → log warning, skip entry
- [ ] Database connection loss → graceful error message

#### Analytics Tests
- [ ] Hit rate calculation correct: worked / (worked + didn't)
- [ ] Expected value: (hit_rate × $100) - ((1-hit_rate) × $100)
- [ ] Filters work correctly (region, day, date range)
- [ ] Correlation insights show realistic patterns

---

## Implementation Location & Architecture

### New Django App: `MarketOpenCapture` (Recommended)

**Why separate app?**
- Keeps concerns isolated
- FutureTrading focuses on live quotes + signals
- MarketOpenCapture focuses on historical sessions + grading
- Easy to enable/disable independently

**Alternative:** Extend `FutureTrading` app with new models/views

### File Structure (New App)

```
thor-backend/
├── MarketOpenCapture/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # MarketOpenSession, SymbolSnapshot, etc.
│   ├── views.py               # API endpoints (today, history)
│   ├── urls.py
│   ├── admin.py               # Django admin panels
│   ├── signals.py             # Django signal handlers (market open event)
│   ├── tasks.py               # Celery tasks (capture, grader)
│   ├── services/
│   │   ├── capture.py         # Snapshot capture logic
│   │   ├── grader.py          # Outcome grading logic
│   │   └── analytics.py       # Hit rate, EV calculations
│   ├── management/
│   │   └── commands/
│   │       ├── listen_market_opens.py    # Monitor timezone app
│   │       ├── grade_pending_sessions.py # Manual grader runner
│   │       └── seed_symbol_config.py     # Initial config data
│   ├── migrations/
│   └── tests/
│       ├── test_capture.py
│       ├── test_grader.py
│       └── test_analytics.py
```

### Database Models (Detailed)

#### 1. MarketOpenSession
```python
from django.db import models
from django.utils import timezone

class MarketSession(models.Model):
    """One record per region per day when market opens."""
    
    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    region = models.CharField(max_length=50)  # "Japan", "USA", etc.
    opened_at = models.DateTimeField()  # Timezone-aware
    date = models.DateField()  # For uniqueness check
    day_of_week = models.CharField(max_length=10)  # "Monday", etc.
    
    # Composite signal at market open
    bhs = models.CharField(max_length=20)  # BUY, SELL, HOLD
    weight = models.IntegerField()  # Numeric score
    weighted_average = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    
    # YM entry details
    ym_entry_side = models.CharField(max_length=10, null=True)  # BUY, SELL, None
    ym_entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ym_bid_at_open = models.DecimalField(max_digits=10, decimal_places=2)
    ym_ask_at_open = models.DecimalField(max_digits=10, decimal_places=2)
    ym_last_at_open = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ym_spread_at_open = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Target/stop prices (calculated at entry)
    ym_target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ym_stop_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Outcome
    ym_outcome = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Worked', 'Worked'),
            ('Didn\'t Work', 'Didn\'t Work'),
            ('Expired', 'Expired'),
            ('No Entry', 'No Entry'),
            ('Error', 'Error'),
        ],
        default='Pending'
    )
    ym_pnl_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ym_resolved_at = models.DateTimeField(null=True)
    resolution_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    resolution_reason = models.CharField(max_length=100, null=True)
    
    # Configuration
    evaluation_window_sec = models.IntegerField(default=1800)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['region', 'date']]
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['region', 'date']),
            models.Index(fields=['date', 'ym_outcome']),
        ]
    
    def __str__(self):
        return f"{self.region} {self.date} - {self.ym_outcome}"
```

#### 2. SymbolSnapshot
```python
class SymbolSnapshot(models.Model):
    """11 records per session, one for each futures symbol."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey(MarketOpenSession, related_name='snapshots', on_delete=models.CASCADE)
    
    # Symbol info
    symbol = models.CharField(max_length=10)
    captured_at = models.DateTimeField()
    
    # Prices at open
    bid = models.DecimalField(max_digits=15, decimal_places=6)
    ask = models.DecimalField(max_digits=15, decimal_places=6)
    last = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    spread = models.DecimalField(max_digits=15, decimal_places=6)
    volume = models.IntegerField(null=True)
    
    # OHLC
    open = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    high = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    low = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    close = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    change = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    
    # HBS classification
    hbs_classification = models.CharField(max_length=20)  # Strong Buy, Buy, etc.
    hbs_weight = models.IntegerField()  # -2, -1, 0, 1, 2
    
    # Symbol config (from reference table)
    tick_size = models.DecimalField(max_digits=10, decimal_places=6)
    tick_value_usd = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Theoretical trade (if we had traded this symbol)
    theoretical_entry_side = models.CharField(max_length=10, null=True)
    theoretical_entry_price = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    theoretical_target_price = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    theoretical_stop_price = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    
    class Meta:
        ordering = ['symbol']
        indexes = [
            models.Index(fields=['session', 'symbol']),
        ]
    
    def __str__(self):
        return f"{self.session.region} {self.session.date} - {self.symbol}"
```

#### 3. SymbolConfig (Reference Data)
```python
class SymbolConfig(models.Model):
    """Reference table for symbol tick values and targets."""
    
    symbol = models.CharField(max_length=10, unique=True)
    tick_size = models.DecimalField(max_digits=10, decimal_places=6)
    tick_value_usd = models.DecimalField(max_digits=10, decimal_places=2)
    take_profit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    stop_loss_usd = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    display_precision = models.IntegerField(default=2)
    contract_size = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_target_ticks(self):
        """Calculate how many ticks for $100 profit."""
        return float(self.take_profit_usd) / float(self.tick_value_usd)
    
    def __str__(self):
        return f"{self.symbol} - ${self.tick_value_usd}/tick"
```

#### 4. GlobalConfig
```python
class GlobalConfig(models.Model):
    """Global settings for capture and grading."""
    
    config_key = models.CharField(max_length=50, unique=True)
    config_value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.config_key}: {self.config_value}"
```

#### 5. MissedCapture (Error Tracking)
```python
class MissedCapture(models.Model):
    """Log when a capture fails."""
    
    region = models.CharField(max_length=50)
    opened_at = models.DateTimeField()
    error = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Missed: {self.region} {self.opened_at}"
```

---

## Integration with Existing Apps

### Timezone App Listener

**Option A: Django Signals** (if timezone app emits signals)
```python
# MarketOpenCapture/signals.py
from django.dispatch import receiver
from timezones.signals import market_status_changed  # hypothetical

@receiver(market_status_changed)
def on_market_open(sender, market, **kwargs):
    if market.status == 'OPEN':
        # Trigger capture
        from .tasks import capture_market_open
        capture_market_open.delay(market.country, market.opened_at)
```

**Option B: Management Command** (polling)
```python
# MarketOpenCapture/management/commands/listen_market_opens.py
from django.core.management.base import BaseCommand
from timezones.models import Market
from MarketOpenCapture.tasks import capture_market_open

class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            markets = Market.objects.filter(is_active=True, status='OPEN')
            for market in markets:
                # Check if we've captured today
                if should_capture(market.country, timezone.now()):
                    capture_market_open.delay(market.country, timezone.now())
            time.sleep(60)  # Check every minute
```

### FutureTrading Integration

**Capture service calls existing endpoint:**
```python
# MarketOpenCapture/services/capture.py
import requests

def fetch_futuretrading_snapshot():
    """Get enriched futures data with composite signal."""
    response = requests.get(
        'http://localhost:8000/api/futuretrading/quotes/latest',
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def extract_ym_data(snapshot):
    """Extract YM-specific data from snapshot."""
    for row in snapshot['rows']:
        if row['instrument']['symbol'] == 'YM':
            return {
                'bid': row['bid'],
                'ask': row['ask'],
                'last': row['last'],
                'spread': row.get('spread', 0),
                'signal': row['extended_data']['signal']
            }
    raise ValueError("YM not found in snapshot")
```

### LiveData Integration (Grading)

**Grader service polls current prices:**
```python
# MarketOpenCapture/services/grader.py
import requests

def get_current_ym_price():
    """Get current YM bid price from LiveData."""
    response = requests.get(
        'http://localhost:8000/api/feed/quotes/snapshot/',
        params={'symbols': 'YM'},
        timeout=5
    )
    data = response.json()
    quotes = data.get('quotes', [])
    if quotes:
        return quotes[0].get('bid')
    return None

def check_target_or_stop_hit(session, current_bid):
    """Check if target or stop price hit.
    
    For BUY entries: check if bid >= target or bid <= stop
    For SELL entries: check if bid <= target or bid >= stop
    """
    if session.ym_entry_side == 'BUY':
        if current_bid >= session.ym_target_price:
            return 'Worked'
        elif current_bid <= session.ym_stop_price:
            return 'Didn\'t Work'
    elif session.ym_entry_side == 'SELL':
        if current_bid <= session.ym_target_price:
            return 'Worked'
        elif current_bid >= session.ym_stop_price:
            return 'Didn\'t Work'
    
    return None  # Neither hit yet
```

---

## Next Steps (Before Writing Code)

### Confirmations Needed from User:

1. **Tick values table** - Verify all 11 symbols' tick sizes and values are correct
2. **TOTAL composite thresholds** - Confirm the >9, 3-9, -3 to +3, etc. ranges
3. **Evaluation window** - Confirm 30 minutes default is appropriate
4. **Grading frequency** - Is 5-10 second polling acceptable, or need tick-level?
5. **Timezone regions** - Confirm the 7 main regions to monitor (Japan, China, India, EuroNext, London, Pre_USA, USA)
6. **Bear market instruments** - Confirm VX, DX, GC, ZB are the only ones with inverted weights
7. **App structure** - Prefer separate `MarketOpenCapture` app or extend `FutureTrading`?

### Design Documents to Create:

1. ✅ **Phase 1 Spec** - This document (done!)
2. ⏳ **Phase 2 Diagram** - Visual event flow with swimlanes
3. ⏳ **Phase 3 Config Sheet** - Editable CSV/Excel with all symbol configs
4. ⏳ **Phase 4 Ops Notes** - Deployment, monitoring, troubleshooting guide
5. ⏳ **Phase 5 Wireframes** - UI mockups for today/history views
6. ⏳ **Phase 6 Test Plan** - Detailed test cases with expected results

### Technical Decisions to Make:

1. **Celery vs Django-Q vs Threading** - Which background task system?
2. **Postgres vs TimescaleDB** - Will session data volume justify time-series DB?
3. **REST vs GraphQL** - Simple REST sufficient or need GraphQL for complex queries?
4. **Real-time updates** - WebSockets now or later phase?
5. **Frontend framework** - React (existing) or need separate dashboard?

---

## Appendix: Excel Mapping

### Your Excel "Row 14" → Our System

**Excel Columns (from screenshots):**
- `YM-1`, `ES-1`, `NQ-1`, etc. → Symbol names
- `Time` → Captured timestamp → `MarketOpenSession.opened_at`
- `Num` → ? (needs clarification)
- `Perc` → ? (percentage change?)
- `Bid`, `Ask` → Entry prices → `SymbolSnapshot.bid`, `SymbolSnapshot.ask`
- `Offset value` → Target/stop offset → Calculated from tick values

**Excel Logic (as we understand it):**
1. Market opens → capture all 11 symbols
2. TOTAL weighted average determines direction
3. For YM: record entry price (bid or ask based on direction)
4. Calculate target = entry ± offset (in ticks)
5. Monitor if target hit within window
6. Record outcome in adjacent cell (Worked/Didn't)

**Our System Equivalent:**
1. Timezone status → "OPEN" trigger
2. Call FutureTrading API → get TOTAL composite
3. Create MarketOpenSession + 11 SymbolSnapshots
4. For YM: calculate target/stop from SymbolConfig
5. Grader task monitors LiveData prices
6. Update session.ym_outcome when resolved

---

## Risk Assessment

### High Risks
1. **Data latency** - TOS Excel RTD might lag during volatile opens
   - **Mitigation:** Accept as-is for MVP, note timestamp delays
   
2. **Grader accuracy** - 5-second polling might miss quick target hits
   - **Mitigation:** Start with polling, upgrade to Redis streaming later

3. **Timezone complexity** - DST changes, holiday edge cases
   - **Mitigation:** Use pytz library, rely on timezone app's logic

### Medium Risks
1. **Database growth** - 11 snapshots × 7 regions × 250 trading days = ~20K rows/year
   - **Mitigation:** Normal growth, add archival strategy after 2+ years

2. **Celery reliability** - Background tasks might fail silently
   - **Mitigation:** Add monitoring, retry logic, error alerts

### Low Risks
1. **API endpoint failures** - FutureTrading/LiveData might be down
   - **Mitigation:** Retry logic + MissedCapture logging

---

## Success Metrics

### Technical Metrics
- [ ] 99%+ capture success rate (no missed market opens)
- [ ] <500ms API response time for today view
- [ ] <2 second end-to-end capture latency
- [ ] Zero duplicate sessions per region/day

### Business Metrics
- [ ] Can answer: "What's my hit rate for Japan Mondays?"
- [ ] Can answer: "Which region has best expected value?"
- [ ] Can answer: "Does ES signal predict YM better than NQ?"
- [ ] Dashboard loads in <1 second with 30 days of history

### User Satisfaction
- [ ] User can trust data accuracy (audit trail complete)
- [ ] User can export data to Excel for custom analysis
- [ ] User can backtest strategy changes (replay historical captures)

---

## Timeline Estimate (Once Design Approved)

### Phase 1: Core Models & Config (1-2 days)
- Create Django app structure
- Define models
- Write migrations
- Seed symbol config data
- Django admin panels

### Phase 2: Capture Logic (2-3 days)
- Timezone listener (management command or signal)
- Snapshot capture service
- Integration with FutureTrading API
- Idempotency checks
- Error handling

### Phase 3: Grader Logic (2-3 days)
- Background task setup (Celery)
- Price polling service
- Target/stop detection
- Outcome recording
- Window expiration handling

### Phase 4: API Endpoints (1-2 days)
- Today view endpoint
- History view endpoint
- Analytics calculations
- Filters and pagination

### Phase 5: Frontend UI (2-3 days)
- Today view page
- History/analytics page
- Charts and tables
- Real-time updates (optional)

### Phase 6: Testing & Deployment (2 days)
- Unit tests
- Integration tests
- UAT with recorded data
- Deployment to dev/prod

**Total: 10-15 days** (assuming full-time, no blockers)

---

## Questions for User (Awaiting Answers)

1. ❓ Confirm tick values table accuracy (especially ZB's 1/32 tick size)
2. ❓ What are "Num" and "Perc" columns in your Excel?
3. ❓ Preferred background task system (Celery, Django-Q, other)?
4. ❓ Real-time updates needed in MVP or later phase?
5. ❓ Any specific analytics/queries you want to run that aren't listed?
6. ❓ Should we track theoretical outcomes for all 11 symbols, or just record snapshots?
7. ❓ Any regional nuances (e.g., Pre_USA needs different logic)?

---

**Status:** ✅ Design complete, awaiting user confirmation to proceed with implementation

**Next Action:** User reviews this document, answers questions, approves design → we begin coding

**Document Maintainer:** GitHub Copilot + User (sutto)  
**Last Updated:** October 25, 2025
