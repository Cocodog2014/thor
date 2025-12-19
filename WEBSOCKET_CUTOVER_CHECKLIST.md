# WebSocket Cutover - Pre-Integration Checklist

## ✅ Infrastructure Complete

- [x] ASGI application (`thor_project/asgi.py`)
- [x] WebSocket routing (`thor_project/routing.py`)
- [x] Consumer implementation (`GlobalMarkets/consumers.py`)
- [x] Consumer tests (5/5 passing)
- [x] Channel layer configuration (Redis)
- [x] Feature flags (`GlobalMarkets/services/websocket_features.py`)
- [x] Message builders (`GlobalMarkets/services/websocket_broadcast.py`)
- [x] Broadcast helpers (sync + async)
- [x] Heartbeat integration (`GlobalMarkets/services/heartbeat.py`)
- [x] Frontend WebSocket manager (`src/services/websocket.ts`)
- [x] Frontend cutover controller (`src/services/websocket-cutover.ts`)
- [x] Frontend hooks (`src/hooks/useWebSocket.ts`)
- [x] Frontend awareness hooks (`src/hooks/useWebSocketAware.ts`)
- [x] Shadow monitor component (`src/components/WebSocketShadowMonitor.tsx`)
- [x] Example components (`src/components/WebSocketCutoverExample.tsx`)

## ✅ Documentation Complete

- [x] WebSocket cutover plan (`WEBSOCKET_CUTOVER_PLAN.md`)
- [x] Integration guide (`WEBSOCKET_INTEGRATION_GUIDE.md`)
- [x] Status check script (`scripts/check_cutover_status.py`)
- [x] Code examples (in integration guide)
- [x] Debugging guide (in integration guide)
- [x] Rollback plan (in integration guide)

## ⏳ Next Steps (In Order)

### Phase 1: Job Integration (This Week)

**Search for these jobs in `ThorTrading/services/stack_start.py` and `GlobalMarkets/services/heartbeat.py`:**

- [ ] Find `IntradayJob` - handles intraday bars (1s)
- [ ] Find `AccountBalanceJob` or similar - handles account balance (10s)
- [ ] Find `PositionsJob` or similar - handles positions (10s)
- [ ] Find `MarketMetricsJob` - handles market status (10s)

**For each job, add broadcast call:**

```python
# At the end of job.execute():
from GlobalMarkets.services.websocket_features import WebSocketFeatureFlags
from GlobalMarkets.services.websocket_broadcast import broadcast_to_websocket_sync

if WebSocketFeatureFlags().is_<feature>_enabled():
    msg = build_<feature>_message(data)
    broadcast_to_websocket_sync(channel_layer, msg)
```

### Phase 2: Shadow Mode Testing (1-2 Days)

- [ ] Start server with Daphne (ASGI)
- [ ] Run market session (BackTest or Paper)
- [ ] Check console for `[WS]` messages
- [ ] Compare with REST endpoint responses
- [ ] Document observed behavior

### Phase 3: Feature Cutover (1 Feature/Week)

**Week 1 - Account Balance:**
- [ ] `export WS_FEATURE_ACCOUNT_BALANCE=true`
- [ ] Run market session, verify messages
- [ ] Compare REST vs WebSocket payloads
- [ ] Monitor 2-3 sessions for stability
- [ ] Delete REST timer from registry
- [ ] Delete REST endpoint from views

**Week 2 - Positions:**
- [ ] Repeat for positions feature

**Week 3 - Intraday Bars:**
- [ ] Repeat for intraday feature

**Week 4 - Global Market:**
- [ ] Repeat for global market feature

### Phase 4: Cleanup (End of Month)

- [ ] Remove all REST endpoints
- [ ] Remove all REST timers
- [ ] Update documentation (mark complete)
- [ ] Final verification
- [ ] Tag release

## 🔧 Testing Commands

```bash
# Check cutover status
python manage.py shell < scripts/check_cutover_status.py

# Run consumer tests
python manage.py test GlobalMarkets.tests.test_consumers

# Monitor heartbeat in Redis
redis-cli SUBSCRIBE market_data

# Watch WebSocket messages (backend)
tail -f logs/django.log | grep "\[WS\]"

# Check feature flag
echo $WS_FEATURE_ACCOUNT_BALANCE
```

## 📋 Shadow Mode Behavior

During shadow mode (all flags false):

- REST endpoints active → return current data
- WebSocket server running → broadcasts messages every 30 ticks
- Messages logged → console shows `[WS]` prefixed logs
- No data changes → REST remains source of truth

Expected console output:
```
[WS] heartbeat: {"timestamp": "2025-01-15T10:30:00Z", "active_jobs": 8, ...}
[WS] intraday_bar: {"symbol": "SPY", "timestamp": "...", "open": 123.45, ...}
[WS] account_balance: {"cash": 100000, "portfolio_value": 150000, ...}
```

## ⚡ First Cutover Checklist (Account Balance)

```bash
# 1. Enable feature
export WS_FEATURE_ACCOUNT_BALANCE=true

# 2. Restart server (or auto-reload)
# Watch logs for: ✅ PARTIAL CUTOVER - account_balance using WebSocket

# 3. Run market session
# Watch console for: [WS] account_balance: {...}

# 4. Verify data
# Compare with: GET /api/account/balance/

# 5. Monitor 2-3 sessions
# Check stability, consistency, no errors

# 6. Once confirmed, find REST timer
grep -r "AccountBalanceJob\|get_account_balance" ThorTrading/ GlobalMarkets/

# 7. Delete timer registration
# Edit: ThorTrading/services/stack_start.py
# Remove: registry.register(AccountBalanceJob, ...)

# 8. Delete REST endpoint
# Edit: ThorTrading/views.py or GlobalMarkets/views.py
# Delete: @api_view('GET') def account_balance(request): ...

# 9. Verify deletion
grep -r "AccountBalanceJob\|get_account_balance" ThorTrading/ GlobalMarkets/
# Should return: no results (or only WebSocket references)

# 10. Commit
git add -A
git commit -m "Cutover account_balance to WebSocket - REST timer and endpoint removed"
```

## 🎯 Current Status

**Infrastructure**: ✅ Complete and tested
**Documentation**: ✅ Comprehensive guides created
**Next Action**: Find job classes and add broadcast calls
**Timeline**: 4 weeks (1 feature per week)
**Risk Level**: 🟢 Low (REST remains active, zero downtime)

## 📞 Support

If you get stuck:

1. Check `WEBSOCKET_INTEGRATION_GUIDE.md` → Debugging section
2. Check consumer tests: `GlobalMarkets/tests/test_consumers.py`
3. Check example components: `src/components/WebSocketCutoverExample.tsx`
4. Check broadcast helpers: `GlobalMarkets/services/websocket_broadcast.py`

## Quick Links

- **Integration Guide**: `WEBSOCKET_INTEGRATION_GUIDE.md`
- **Cutover Plan**: `WEBSOCKET_CUTOVER_PLAN.md`
- **Feature Flags**: `GlobalMarkets/services/websocket_features.py`
- **Broadcast Helpers**: `GlobalMarkets/services/websocket_broadcast.py`
- **Frontend Manager**: `src/services/websocket-cutover.ts`
- **Example Components**: `src/components/WebSocketCutoverExample.tsx`
- **Consumer Code**: `GlobalMarkets/consumers.py`
- **Tests**: `GlobalMarkets/tests/test_consumers.py`

---

**Ready to integrate! Each job needs 2-3 lines of code to start broadcasting.**
