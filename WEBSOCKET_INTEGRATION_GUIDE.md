## WebSocket Cutover Integration Guide

### Current Status
- ✅ **Infrastructure**: ASGI, routing, consumer, tests (5/5 passing)
- ✅ **Shadow Mode**: Heartbeat broadcasts, frontend logging
- ✅ **Cutover System**: Feature flags, message builders, broadcast helpers
- ⏳ **Next**: Integrate into job classes

---

## Phase 1: Integration (Next Steps)

### Step 1.1: Find Jobs That Handle Each Feature

```bash
# Backend job registry
# File: GlobalMarkets/services/heartbeat.py → JobRegistry

Account Balance:
  - Job: AccountBalanceJob (if exists) or IntradayJob
  - Current Timer: ~10s interval
  - Location: ThorTrading/services/stack_start.py

Positions:
  - Job: PositionsJob (if exists) or IntradayJob
  - Current Timer: ~10s interval
  - Location: ThorTrading/services/stack_start.py

Intraday Bars:
  - Job: IntradayJob
  - Current Timer: ~1s interval
  - Location: ThorTrading/services/stack_start.py

Global Market (Market Status):
  - Job: MarketMetricsJob
  - Current Timer: ~10s interval
  - Location: ThorTrading/services/stack_start.py or GlobalMarkets/services/heartbeat.py
```

### Step 1.2: Add WebSocket Broadcast to Each Job

**Pattern** (apply to each job):

```python
# At top of job's execute() method
from GlobalMarkets.services.websocket_features import WebSocketFeatureFlags
from GlobalMarkets.services.websocket_broadcast import broadcast_to_websocket_sync

class IntradayJob(BaseJob):
    def execute(self):
        # Existing code that updates database
        bars = self.fetch_and_store_intraday_bars()
        
        # NEW: Broadcast to WebSocket (if feature enabled)
        if WebSocketFeatureFlags().is_intraday_enabled():
            for bar in bars:
                msg = build_intraday_bar_message(bar)
                broadcast_to_websocket_sync(channel_layer, msg)
```

### Step 1.3: Wire Channel Layer Into Jobs

**In `stack_start.py`:**

```python
from channels.layers import get_channel_layer

# Get channel layer once at startup
channel_layer = get_channel_layer()

# Pass to jobs that broadcast
intraday_job = IntradayJob(channel_layer=channel_layer)
account_balance_job = AccountBalanceJob(channel_layer=channel_layer)
# etc.
```

---

## Phase 2: Testing Shadow Mode (Before Cutover)

### Step 2.1: Start Server in Shadow Mode

```bash
# Terminal 1: Start backend (ASGI + WebSocket)
cd /path/to/thor-backend
daphne -b 0.0.0.0 -p 8000 thor_project.asgi:application

# Terminal 2: Check cutover status
python manage.py shell < scripts/check_cutover_status.py
```

Expected output:
```
🔌 WebSocket Cutover Status
==========================================================
⚪ SHADOW MODE - All features using REST (WebSocket logging)

Per-Feature Status:
  ⚪ REST     account_balance      (set WS_FEATURE_ACCOUNT_BALANCE=true to enable)
  ⚪ REST     positions             (set WS_FEATURE_POSITIONS=true to enable)
  ⚪ REST     intraday              (set WS_FEATURE_INTRADAY=true to enable)
  ⚪ REST     global_market         (set WS_FEATURE_GLOBAL_MARKET=true to enable)
```

### Step 2.2: Run Market Session and Check Console

1. Open frontend in browser (e.g., http://localhost:5173)
2. Open DevTools (F12) → Console
3. Run a market session (BackTest or Paper Trading)
4. Look for messages like:
   ```
   [WS] heartbeat: {timestamp, active_jobs, ...}
   [WS] intraday_bar: {symbol, timestamp, open, high, low, close, volume, ...}
   [WS] account_balance: {cash, portfolio_value, ...}
   ```

Expected: All messages logged regardless of feature flag (shadow mode)

### Step 2.3: Compare with REST Endpoint

Run market session and compare:
- **WebSocket** (console): `[WS] account_balance: {...}`
- **REST** (network tab or curl): `GET /api/account/balance/`

Should match exactly.

---

## Phase 3: Feature-by-Feature Cutover

### Cutover Sequence
1. **Account Balance** (10s interval)
2. **Positions** (10s interval)  
3. **Intraday Bars** (1s interval)
4. **Global Market** (10s interval)

### For Each Feature:

#### Step 3.1: Enable Feature Flag

```bash
# Terminal 1: Set environment variable
export WS_FEATURE_ACCOUNT_BALANCE=true

# Restart server (or server auto-reloads)
```

Check status:
```
✅ PARTIAL CUTOVER - Some features using WebSocket

Per-Feature Status:
  ✅ WS         account_balance      (WS_FEATURE_ACCOUNT_BALANCE=true)
  ⚪ REST       positions             (set WS_FEATURE_POSITIONS=true to enable)
  ⚪ REST       intraday              (set WS_FEATURE_INTRADAY=true to enable)
  ⚪ REST       global_market         (set WS_FEATURE_GLOBAL_MARKET=true to enable)
```

#### Step 3.2: Run 1-2 Full Market Sessions

- Watch console for `[WS] account_balance:` messages
- Verify data appears at ~10s intervals
- Compare with previous REST response

#### Step 3.3: Verify Data Integrity

Checklist:
- [ ] Messages appear at expected interval (10s for balance)
- [ ] Payload contains all expected fields (cash, portfolio_value, timestamp, etc.)
- [ ] Values match REST endpoint response
- [ ] No console errors logged
- [ ] Websocket connection stable (not reconnecting excessively)

#### Step 3.4: Delete REST Timer

Once verified:

```bash
# File: ThorTrading/services/stack_start.py

# Find and comment out/delete:
# registry.register(AccountBalanceJob, ...)

# Then commit:
git add -A
git commit -m "Cutover account_balance to WebSocket - REST timer removed"
```

### Verification Script

```python
# Run after enabling feature flag
from GlobalMarkets.services.websocket_features import WebSocketFeatureFlags
from GlobalMarkets.services.websocket_broadcast import build_account_balance_message

flags = WebSocketFeatureFlags()

# Check flag
assert flags.is_account_balance_enabled(), "Flag not set!"

# Check message builder
sample_balance = {
    'cash': 100000,
    'portfolio_value': 150000,
    'timestamp': '2025-01-15T10:30:00Z'
}
msg = build_account_balance_message(sample_balance)
assert msg['type'] == 'account_balance'
assert msg['data']['cash'] == 100000

print("✅ Verification passed - ready to delete REST timer")
```

---

## Phase 4: Post-Cutover Cleanup

### After All 4 Features Cutover Complete:

1. **Delete REST Endpoints**:
   ```bash
   # Delete from ThorTrading/views.py or GlobalMarkets/views.py
   # Delete: account_balance(), positions(), intraday_bars(), market_status()
   ```

2. **Delete URL Mappings**:
   ```bash
   # Delete from urls.py
   # Delete all /api/account/balance/, /api/positions/, etc.
   ```

3. **Update Documentation**:
   ```bash
   # Update WEBSOCKET_CUTOVER_PLAN.md → mark "COMPLETE"
   # Update this guide → completion date
   ```

4. **Final Verification**:
   ```bash
   # Ensure no REST timer code remains
   git grep "AccountBalanceJob\|PositionsJob\|IntraDayJob" | grep -v "WebSocket"
   # Should return nothing (except WebSocket references)
   ```

---

## Rollback Plan

**If any feature is unstable:**

```bash
# Immediately disable feature
export WS_FEATURE_ACCOUNT_BALANCE=false

# Server will fall back to REST within seconds
# Check cutover status
python manage.py shell < scripts/check_cutover_status.py
# Should show ⚪ REST again for that feature
```

**Zero downtime** - REST endpoints remain active during cutover period.

---

## Debugging

### Console Logs Not Appearing?

1. Check WebSocket connection in browser DevTools:
   - Network tab → Filter by "WS" or "WebSocket"
   - Should see: `ws://localhost:8000/ws/`
   - Status: "101 Switching Protocols"

2. Check browser console for errors:
   - `useWebSocket` hook should show connection message

3. Check backend logs:
   - `daphne` should show connection accepted
   - `[WS] consumer.connect()` message

### Messages Not Broadcasting?

1. Check Redis is running:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. Check feature flag is enabled:
   ```bash
   echo $WS_FEATURE_ACCOUNT_BALANCE
   # Should return: true
   ```

3. Check job is executing:
   ```bash
   # In Django shell
   from GlobalMarkets.services.heartbeat import JobRegistry
   registry = JobRegistry()
   print(registry.registry)
   # Should show IntradayJob, etc.
   ```

### Heartbeat Not Broadcasting?

Check `GlobalMarkets/services/heartbeat.py`:
```python
# Should see in logs:
logger.debug(f"Broadcasting heartbeat to WebSocket")
```

If missing:
1. Ensure `channel_layer` is passed to `run_heartbeat()`
2. Check `_send_websocket_message()` is called every 30 ticks
3. Check no exceptions in error handler

---

## Files Modified for Cutover

- ✅ `GlobalMarkets/services/websocket_features.py` - Feature flags
- ✅ `GlobalMarkets/services/websocket_broadcast.py` - Message builders + broadcast
- ✅ `GlobalMarkets/services/heartbeat.py` - Added channel_layer support
- ✅ `GlobalMarkets/consumers.py` - WebSocket consumer with 7 message handlers
- ✅ `ThorTrading/services/stack_start.py` - Pass channel_layer to heartbeat
- ✅ `thor_project/asgi.py` - ASGI application (updated docs)
- ✅ `thor_project/routing.py` - WebSocket URL routing
- ✅ `src/services/websocket.ts` - Frontend WebSocket manager
- ✅ `src/services/websocket-cutover.ts` - Frontend cutover controller
- ✅ `src/hooks/useWebSocket.ts` - WebSocket hooks (updated with logging)
- ✅ `src/hooks/useWebSocketAware.ts` - REST/WebSocket routing helpers
- ✅ `src/components/WebSocketShadowMonitor.tsx` - Status display (updated with feature status)
- ⏳ (Pending) Job classes - Add broadcast calls
- ⏳ (Pending) Frontend components - Use `useWebSocketAware` to route to WS/REST

---

## Timeline

- **Now**: Jobs integrated with broadcast calls
- **Week 1**: Account Balance cutover + verification
- **Week 2**: Positions cutover + verification
- **Week 3**: Intraday Bars cutover + verification
- **Week 4**: Global Market cutover + verification
- **Week 5**: Complete cleanup (delete REST endpoints)
- **Complete**: Full WebSocket migration

---

## Summary

**Current Status**: ✅ All infrastructure ready for job integration

**Next Action**: Find each job class (IntradayJob, AccountBalanceJob, etc.) and add:
```python
if WebSocketFeatureFlags().is_<feature>_enabled():
    msg = build_<feature>_message(data)
    broadcast_to_websocket_sync(channel_layer, msg)
```

**Expected Result**: WebSocket messages start flowing during shadow mode, ready for cutover.
