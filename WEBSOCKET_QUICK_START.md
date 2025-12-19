# WebSocket Cutover - Quick Start

## 🎯 Current Status
✅ All infrastructure complete. Ready for job integration.

## 📖 Read This First

1. **Quick Overview** (5 min): [WEBSOCKET_CUTOVER_STATUS.md](WEBSOCKET_CUTOVER_STATUS.md)
2. **Detailed Guide** (15 min): [WEBSOCKET_INTEGRATION_GUIDE.md](WEBSOCKET_INTEGRATION_GUIDE.md)
3. **Feature Plan** (10 min): [WEBSOCKET_CUTOVER_PLAN.md](WEBSOCKET_CUTOVER_PLAN.md)
4. **Task List** (5 min): [WEBSOCKET_CUTOVER_CHECKLIST.md](WEBSOCKET_CUTOVER_CHECKLIST.md)

## ⚡ TL;DR - What You Need to Do

### Step 1: Find Jobs (10 min)

```bash
grep -n "registry.register" ThorTrading/services/stack_start.py
```

Look for:
- IntradayJob
- AccountBalanceJob (or similar)
- PositionsJob (or similar)  
- MarketMetricsJob (or similar)

### Step 2: Add Broadcast Calls (5 min per job)

Open each job class and find the `execute()` method. At the end, add:

```python
# Example for IntradayJob
def execute(self):
    # ... existing code that updates database ...
    
    # NEW: Broadcast to WebSocket
    from GlobalMarkets.services.websocket_features import WebSocketFeatureFlags
    from GlobalMarkets.services.websocket_broadcast import broadcast_to_websocket_sync, build_intraday_bar_message
    
    if WebSocketFeatureFlags().is_intraday_enabled():
        for bar in bars:
            msg = build_intraday_bar_message(bar)
            broadcast_to_websocket_sync(self.channel_layer, msg)
```

**Copy-paste from integration guide** → Step 1.2 for exact patterns.

### Step 3: Test Shadow Mode (1 day)

```bash
# Terminal 1: Start server
cd /path/to/thor-backend
daphne -b 0.0.0.0 -p 8000 thor_project.asgi:application

# Terminal 2: Check status
python manage.py shell < scripts/check_cutover_status.py
# Should show: ⚪ SHADOW MODE

# Browser: Open DevTools (F12) → Console
# Run market session
# Should see: [WS] heartbeat, [WS] intraday_bar, etc.
```

### Step 4: First Feature Cutover (1 week)

```bash
# Enable account balance feature
export WS_FEATURE_ACCOUNT_BALANCE=true
# Restart server (auto-reload)

# Run market session, verify messages appear
# Compare with REST endpoint response
# Run 2-3 sessions with no issues

# Once verified, find and delete REST timer:
grep -n "AccountBalanceJob\|get_account_balance" ThorTrading/services/stack_start.py

# Edit file and remove the timer registration
# Edit file and remove the REST endpoint from views

# Commit:
git add -A
git commit -m "Cutover account_balance to WebSocket"
```

### Step 5: Repeat for Other Features

Do the same for:
- Positions (Week 2)
- Intraday (Week 3)
- Global Market (Week 4)

## 📚 Documentation Map

| Need | File |
|------|------|
| Overview | [WEBSOCKET_CUTOVER_STATUS.md](WEBSOCKET_CUTOVER_STATUS.md) |
| Integration steps | [WEBSOCKET_INTEGRATION_GUIDE.md](WEBSOCKET_INTEGRATION_GUIDE.md) |
| Feature payloads | [WEBSOCKET_CUTOVER_PLAN.md](WEBSOCKET_CUTOVER_PLAN.md) |
| Task checklist | [WEBSOCKET_CUTOVER_CHECKLIST.md](WEBSOCKET_CUTOVER_CHECKLIST.md) |
| Code examples | [src/components/WebSocketCutoverExample.tsx](thor-frontend/src/components/WebSocketCutoverExample.tsx) |

## 🔧 Key Files

### Backend (Add broadcast calls)
- `ThorTrading/services/stack_start.py` - Find jobs here
- `GlobalMarkets/services/websocket_features.py` - Feature flags (READ ONLY)
- `GlobalMarkets/services/websocket_broadcast.py` - Broadcast helpers (READ ONLY)
- `GlobalMarkets/services/heartbeat.py` - Heartbeat already broadcasts (READ ONLY)
- `scripts/check_cutover_status.py` - Run to check status

### Frontend (Optional - shows which source)
- `src/hooks/useWebSocketAware.ts` - Use in components
- `src/components/WebSocketCutoverExample.tsx` - Copy patterns
- `src/components/WebSocketShadowMonitor.tsx` - Already shows status

## ✅ Checklist

### Before Starting
- [ ] Read WEBSOCKET_CUTOVER_STATUS.md (overview)
- [ ] Understand architecture (in status doc)
- [ ] Read WEBSOCKET_INTEGRATION_GUIDE.md (detailed steps)

### Job Integration Phase
- [ ] Find all 4 jobs
- [ ] Add broadcast calls to each
- [ ] Test compiles, no import errors

### Shadow Mode Phase
- [ ] Start server with Daphne
- [ ] Check cutover status script
- [ ] Run market session
- [ ] See `[WS]` messages in console
- [ ] Compare REST vs WebSocket payloads

### First Cutover (Account Balance)
- [ ] Set `WS_FEATURE_ACCOUNT_BALANCE=true`
- [ ] Verify messages in console
- [ ] Run 2-3 full sessions
- [ ] Find REST timer registration
- [ ] Delete REST timer
- [ ] Find REST endpoint
- [ ] Delete REST endpoint
- [ ] Commit changes
- [ ] Verify no REST code remains

### Repeat for Other Features
- [ ] Positions
- [ ] Intraday  
- [ ] Global Market

### Final Cleanup
- [ ] All REST endpoints deleted
- [ ] All REST timers deleted
- [ ] Update documentation
- [ ] Tag release

## 🚀 Expected Timeline

- **Job Integration**: 2-3 hours (find jobs, add broadcast calls)
- **Shadow Mode Testing**: 1-2 days (verify messages appear)
- **Feature 1 (Account Balance)**: 1 week (test, verify, delete timer)
- **Feature 2 (Positions)**: 1 week
- **Feature 3 (Intraday)**: 1 week
- **Feature 4 (Global Market)**: 1 week
- **Cleanup**: 1 day

**Total**: ~4 weeks

## 🆘 If You Get Stuck

1. Check [WEBSOCKET_INTEGRATION_GUIDE.md](WEBSOCKET_INTEGRATION_GUIDE.md) → Debugging section
2. Check [src/components/WebSocketCutoverExample.tsx](thor-frontend/src/components/WebSocketCutoverExample.tsx) for code patterns
3. Run: `python manage.py test GlobalMarkets.tests.test_consumers`
4. Run: `python manage.py shell < scripts/check_cutover_status.py`

## 💡 Key Concepts

**Shadow Mode**:
- All features using REST endpoints (normal)
- WebSocket running in parallel
- All messages logged to console
- No data changes, just logging

**Feature Cutover**:
- Set `WS_FEATURE_<name>=true`
- That feature switches to WebSocket
- Other features still use REST
- Can rollback instantly (set flag to false)

**Zero Downtime**:
- REST endpoints remain active during cutover
- WebSocket messages tested in shadow mode first
- One feature at a time (isolate issues)
- Immediate rollback if needed

## 📋 One-Pager for Your Manager

✅ **Status**: Infrastructure complete, documentation ready
⏳ **Next**: Add broadcast calls to 4 job classes (2-3 hours)
📅 **Timeline**: 4 weeks for full migration (1 feature/week)
🟢 **Risk**: Low (REST active, instant rollback)
💾 **Approach**: Phased cutover with verification gates

---

**You're ready to start!** → Begin with [WEBSOCKET_INTEGRATION_GUIDE.md](WEBSOCKET_INTEGRATION_GUIDE.md) → Step 1.1
