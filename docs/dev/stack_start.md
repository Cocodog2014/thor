# Thor Background Stack (`stack_start.py`)

**Module:** `FutureTrading/services/stack_start.py`  
**Purpose:** Central, safe startup for all long-running background services in Thor.

This module gives you **one place** to start and manage the core background workers:

- Excel → Redis poller  
- Market Open Grader  
- Market Open Capture loop  

It also includes safety guards so these workers:

- Don’t start during `migrate`, `shell`, `test`, etc.  
- Don’t double-start under Django’s autoreloader  
- Auto-restart if they crash  
- Run as daemon threads alongside `runserver` / gunicorn

---

## 1. High-Level Overview

### What it does

`start_thor_background_stack()`:

1. Checks whether it’s safe to start:
   - Not running a management command like `migrate` or `test`
   - Running in the **main** Django process (`RUN_MAIN == "true"`)
   - Has not already started once in this process
2. Spawns **daemon threads** for each supervisor:
   - `ExcelPollerSupervisor`
   - `MarketOpenGraderSupervisor`
   - `MarketOpenCaptureSupervisor`
3. Returns immediately (non-blocking). Django continues normal startup.

All long-running loops and auto-restarts live inside those supervisor functions.

---

## 2. How It’s Wired Into Django

### `apps.py`

In `FutureTrading/apps.py`, the `ready()` method calls the master stack:

```python
from django.apps import AppConfig

class FuturetradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FutureTrading'

    def ready(self):
        import logging
        logger = logging.getLogger(__name__)

        try:
            from FutureTrading.services.stack_start import start_thor_background_stack
            logger.info("🔥 FutureTrading app ready: initializing background stack...")
            start_thor_background_stack()
            logger.info("🚀 Thor master stack started successfully.")
        except Exception:
            logger.exception("Failed to start Thor master stack")

        # 52-week and Pre-open supervisors are still started here separately
        try:
            from FutureTrading.services.Week52Supervisor import start_52w_monitor_supervisor
            start_52w_monitor_supervisor()
            logger.info("📈 52-week supervisor started.")
        except Exception:
            logger.exception("Failed to start 52w supervisor")

        try:
            from FutureTrading.services.PreOpenBacktestSupervisor import (
                start_preopen_backtest_supervisor,
            )
            start_preopen_backtest_supervisor()
            logger.info("⏰ Pre-open backtest supervisor started.")
        except Exception:
            logger.exception("Failed to start pre-open backtest supervisor")
