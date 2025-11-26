Yep, that makes sense. Let’s lock in **what exactly needs to change in GlobalMarkets** before you touch any code.

Here’s a clear **“change plan”** for the GlobalMarkets app so it becomes *status-only* and fully decoupled from Futures.

---

## 🎯 Goals for GlobalMarkets

1. **GlobalMarkets is purely a world clock / status engine.**

   * Tracks which markets are OPEN/CLOSED.
   * Schedules open/close transitions.
   * Exposes REST APIs and composite index.
   * Emits signals when status changes.

2. **GlobalMarkets does NOT:**

   * Import `FutureTrading` anywhere.
   * Call `capture_market_open` or any futures logic.
   * Know about Redis, futures, or sessions.

3. **Public API / serializers / models stay the same**
   → React UI keeps working with no changes.

---

## 🔧 Files to Change / Clean Up

### 1. `GlobalMarkets/signals.py` — **biggest change**

**Current state:**

* Imports `capture_market_open` from `FutureTrading`.
* On Market `post_save`, if `status == 'OPEN'`, it directly calls `capture_market_open(instance)`.

**What we want:**

* ✅ No import from `FutureTrading`.
* ✅ Emit **signals only** when status changes (CLOSED → OPEN, OPEN → CLOSED).
* ✅ Other apps (like FutureTrading) will listen to those signals later.

**Changes:**

* Remove:

  ```python
  from FutureTrading.views.MarketOpenCapture import capture_market_open
  ...
  if instance.status == 'OPEN' and instance.is_active:
      session = capture_market_open(instance)
  ```

* Replace with:

  * Custom signals: `market_status_changed`, `market_opened`, `market_closed`.
  * Logic that:

    * Loads previous version from DB.
    * Compares `previous.status` vs `instance.status`.
    * Only fires when the status actually changes.
    * Sends the appropriate signals but doesn’t do any work itself.

---

### 2. `GlobalMarkets/monitor.py` — **event scheduler, no capture**

**Current state:**

* Schedules timers.
* When events fire, it:

  * Changes `market.status` and saves.
  * **Directly calls** `capture_market_open(market)` on OPEN transitions.
* `_reconcile_now()` also directly calls capture on already-open markets.

**What we want:**

* ✅ Monitor should **only update `Market.status`**.
* ✅ It should **never call `capture_market_open`** or import `FutureTrading`.
* ✅ Status change will trigger `post_save` → our new signals.

**Changes:**

* Remove any import of `FutureTrading`:

  ```python
  from FutureTrading.views.MarketOpenCapture import capture_market_open
  from GlobalMarkets.models import Market, USMarketStatus  # keep Market, optionally USMarketStatus
  ```

* In `_handle_event()`:

  * Keep logic to compute `target_status = 'OPEN'/'CLOSED'`.
  * If different from current, set `market.status = target_status` and `market.save()`.
  * **Do not** call `capture_market_open`.

* In `_reconcile_now()`:

  * Same: only fix `status` where it’s wrong.
  * No capture calls.

> After this, all side effects are driven by signals, not by monitor.

---

### 3. `GlobalMarkets/management/commands/monitor_markets.py` — **debug-only, no capture**

**Current state:**

* CLI monitor that:

  * Checks markets in a loop.
  * Flips `status` as needed.
  * **Also calls** `capture_market_open(market)` when `target_status == 'OPEN'`.

**What we want:**

* ✅ Use this command only as a manual / debug status synchronizer.
* ✅ No `FutureTrading` import.
* ✅ No capture; just setting `status` and letting signals fire.

**Changes:**

* Remove:

  ```python
  from FutureTrading.views.MarketOpenCapture import capture_market_open
  ...
  if target_status == 'OPEN':
      session = capture_market_open(market)
  ```

* Keep logic that:

  * Calculates `is_open_now`.
  * Updates `market.status` if needed.
  * Logs results.

* Optionally: remove or keep the `USMarketStatus.is_us_market_open_today()` gate depending on whether you want GlobalMarkets to be totally independent of US holidays.

---

### 4. `GlobalMarkets/views.py` (root file) — **legacy, remove/rename**

**Current state:**

* You have:

  * `GlobalMarkets/views/` (package with `viewsets.py` + `composite.py`) → **this is the real one**.
  * `GlobalMarkets/views.py` (root file) → older code with extra markets (Shenzhen, Hong Kong, Spain etc.).

**What we want:**

* ✅ Only one canonical views implementation: the `views/` folder.
* ✅ No confusion for future devs.

**Changes:**

* Rename `GlobalMarkets/views.py` → `views_OLD.py` or move to an `archive/` folder, or delete entirely.
* Do **not** touch `views/viewsets.py` or `views/composite.py` — those are live and used in `urls.py`.

---

### 5. `GlobalMarkets/apps.py` — **confirm startup behavior**

**Current state:**

```python
class GlobalMarketsConfig(AppConfig):
    ...
    def ready(self):
        import GlobalMarkets.signals
        from GlobalMarkets.monitor import start_monitor
        start_monitor()
```

**What we want:**

* ✅ Still import `signals` so our new status signals are active.
* ✅ Still start `MarketMonitor` so status is maintained automatically.
* ❌ Nothing here should import or call `FutureTrading`.

**Changes:**

* Likely **no code change** needed here, as long as:

  * `GlobalMarkets.signals` no longer imports `FutureTrading`.
  * `GlobalMarkets.monitor` no longer imports/calls `FutureTrading`.

---

### 6. `GlobalMarkets/GlobalMarkets.md` — **doc to match new architecture**

You already pasted a basic MD; we drafted a more complete version earlier with:

* Responsibilities
* Models
* Monitor
* Signals
* Management commands
* API endpoints
* React front-end expectations
* Integration with other apps

**Changes:**

* Replace the simple stub MD with the expanded version we wrote (or a trimmed version) that:

  * Explicitly states: **GlobalMarkets does not perform futures capturing**.
  * Mentions the new signals (`market_status_changed`, `market_opened`, `market_closed`).
  * Documents the event-driven monitor.
  * Keeps API contract clear for the front end.

---

## 🧩 Files that should *not* change (for now)

To keep the React front end stable:

* `GlobalMarkets/models.py`
  (Except minor internal changes if you really want, but no field renames / API shape changes.)
* `GlobalMarkets/serializers.py`
* `GlobalMarkets/views/viewsets.py`
* `GlobalMarkets/views/composite.py`
* `GlobalMarkets/urls.py`
* `GlobalMarkets/admin.py` (unless you want cosmetic admin tweaks)

These files are what your UI and external clients hit. Leave them alone and the table you showed in the screenshot will continue to work exactly the same.

---

If you’d like, next step can be:

> “Let’s actually rewrite `signals.py` now”

and I’ll give you a **drop-in replacement** for that file as the first concrete code change.
