# WebSocket Cutover Plan - Phase 3

**Objective:** Replace REST endpoints with WebSocket one feature at a time.

**Pattern:** 
1. Feature broadcasts to WebSocket (shadow mode)
2. Frontend listens and logs messages
3. After verification, set env var to enable feature
4. Delete REST timer once confirmed working

---

## Feature 1: Account Balance

**Env Flag:** `WS_FEATURE_ACCOUNT_BALANCE=true`

**Current REST Timer:**
- `MarketMetricsJob` (10s interval) - updates account balances

**WebSocket Message Type:** `account_balance`

**Payload:**
```json
{
  "type": "account_balance",
  "data": {
    "account_id": 123,
    "account_number": "ACC12345",
    "cash": 50000.00,
    "buying_power": 100000.00,
    "timestamp": "2025-12-19T15:30:00Z"
  }
}
```

**Steps:**
- [ ] 1. Add WebSocket broadcast to account update job
- [ ] 2. Enable shadow mode - verify console logs
- [ ] 3. Set `WS_FEATURE_ACCOUNT_BALANCE=true`
- [ ] 4. Frontend switches from REST to WebSocket
- [ ] 5. Verify no data loss for 1-2 market sessions
- [ ] 6. Delete REST endpoint + timer

---

## Feature 2: Positions

**Env Flag:** `WS_FEATURE_POSITIONS=true`

**Current REST Timer:**
- `MarketMetricsJob` (10s interval) - updates positions

**WebSocket Message Type:** `positions`

**Payload:**
```json
{
  "type": "positions",
  "data": {
    "account_id": 123,
    "positions": [
      {
        "symbol": "SPY",
        "quantity": 100,
        "entry_price": 450.00,
        "current_price": 455.00,
        "pnl": 500.00
      }
    ],
    "timestamp": "2025-12-19T15:30:00Z"
  }
}
```

**Steps:**
- [ ] 1. Add WebSocket broadcast to position update job
- [ ] 2. Enable shadow mode - verify console logs
- [ ] 3. Set `WS_FEATURE_POSITIONS=true`
- [ ] 4. Frontend switches from REST to WebSocket
- [ ] 5. Verify position updates match REST data
- [ ] 6. Delete REST endpoint + timer

---

## Feature 3: Intraday Bars

**Env Flag:** `WS_FEATURE_INTRADAY=true`

**Current REST Timer:**
- `IntradayJob` (1s interval) - captures 1-minute OHLCV bars

**WebSocket Message Type:** `intraday_bar`

**Payload:**
```json
{
  "type": "intraday_bar",
  "data": {
    "country": "USA",
    "symbol": "SPY",
    "timestamp_minute": "2025-12-19T15:30:00Z",
    "open": 450.00,
    "high": 455.50,
    "low": 449.50,
    "close": 453.00,
    "volume": 1250000
  }
}
```

**Steps:**
- [ ] 1. Add WebSocket broadcast to intraday job (fires every minute)
- [ ] 2. Enable shadow mode - verify console logs
- [ ] 3. Set `WS_FEATURE_INTRADAY=true`
- [ ] 4. Frontend switches from REST polling to WebSocket
- [ ] 5. Verify bars match REST endpoint data
- [ ] 6. Delete REST endpoint + timer

---

## Feature 4: Global Market Status

**Env Flag:** `WS_FEATURE_GLOBAL_MARKET=true`

**Current REST Timer:**
- `MarketMetricsJob` (10s interval) - updates market open/close status

**WebSocket Message Type:** `market_status`

**Payload:**
```json
{
  "type": "market_status",
  "data": {
    "market_id": 1,
    "country": "USA",
    "status": "OPEN",
    "seconds_to_next_event": 7200
  }
}
```

**Steps:**
- [ ] 1. Add WebSocket broadcast to market status job
- [ ] 2. Enable shadow mode - verify console logs
- [ ] 3. Set `WS_FEATURE_GLOBAL_MARKET=true`
- [ ] 4. Frontend switches from REST to WebSocket
- [ ] 5. Verify status matches REST endpoint
- [ ] 6. Delete REST endpoint + timer

---

## Verification Checklist (Per Feature)

**Before enabling (`WS_FEATURE_*=true`):**
- [ ] WebSocket messages appear in console logs
- [ ] Message frequency matches REST endpoint (same interval)
- [ ] Message payload has all required fields
- [ ] No WebSocket connection drops during market hours
- [ ] No data loss or gaps in message stream

**After enabling:**
- [ ] Frontend receives data via WebSocket only
- [ ] Data matches REST endpoint (last 1-2 messages)
- [ ] No increase in CPU/memory usage
- [ ] Error logs clean (no WebSocket errors)

**Before deleting REST timer:**
- [ ] Run for 1-2 full market sessions
- [ ] Monitor prod logs for cutover issues
- [ ] Get team sign-off

---

## Environment Setup

Add to `.env` or container env:

```bash
# Shadow mode (all features broadcast, but not yet consuming)
WS_FEATURE_ACCOUNT_BALANCE=false
WS_FEATURE_POSITIONS=false
WS_FEATURE_INTRADAY=false
WS_FEATURE_GLOBAL_MARKET=false

# Gradual cutover (set one to true at a time)
# WS_FEATURE_ACCOUNT_BALANCE=true     # Cutover #1
```

---

## Rollback Plan

If any feature fails after cutover:

1. Set `WS_FEATURE_*=false` immediately
2. Frontend falls back to REST endpoint
3. Delete WebSocket broadcast code (if needed)
4. Investigate and retry

**No data loss because REST timers never deleted until fully verified.**
