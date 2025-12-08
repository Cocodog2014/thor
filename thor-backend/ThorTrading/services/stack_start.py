# ThorTrading/services/stack_start.py

import logging
import os
import sys
import threading
import time

from django.core.management import call_command

logger = logging.getLogger(__name__)


def _truthy_env(name: str, default: str = "0") -> bool:
    value = os.environ.get(name, default)
    return str(value).lower() not in {"0", "false", "no", ""}


GLOBAL_TIMER_ENABLED = _truthy_env("THOR_USE_GLOBAL_MARKET_TIMER", default="1")


# =====================================================================
#  EXCEL → REDIS POLLER SUPERVISOR
# =====================================================================
def start_excel_poller_supervisor():
    """
    Supervisor wrapper for the existing TOS Excel poller.

    Equivalent of:
        python manage.py poll_tos_excel

    Uses Django's call_command so we don't care which app defines it.
    """
    logger.info("📄 Excel Poller Supervisor: starting...")

    while True:
        try:
            logger.info("🚀 Excel Poller: running via call_command('poll_tos_excel')...")
            # This blocks while the command's poll loop runs
            call_command("poll_tos_excel")
            logger.debug("💓 [Excel Poller] exited normally, will restart...")
        except Exception:
            logger.exception("❌ Excel Poller crashed — restarting in 3 seconds...")
            time.sleep(3)


# =====================================================================
#  MARKET OPEN GRADER SUPERVISOR
# =====================================================================
def start_market_open_grader_supervisor():
    """
    Supervisor wrapper for the existing Market Open Grader command.

    Normally run via:
        python manage.py start_market_grader --interval 0.5
    """
    logger.info("📊 Market Open Grader Supervisor: starting...")

    try:
        from ThorTrading.management.commands.start_market_grader import Command

        grader = Command()

        while True:
            try:
                logger.info("🚀 Market Open Grader: running...")
                # Provide interval explicitly; the command expects options['interval']
                grader.handle(interval=0.5)
                logger.debug("💓 [Market Open Grader] alive")
            except Exception:
                logger.exception("❌ Market Open Grader crashed — restarting in 3 seconds...")
                time.sleep(3)

    except Exception:
        logger.exception("❌ Failed to initialize Market Open Grader Supervisor")


# =====================================================================
#  MARKET OPEN CAPTURE SUPERVISOR
# =====================================================================
def start_market_open_capture_supervisor_wrapper():
    """
    Supervisor wrapper for the Market Open Capture logic.

    Expects:
        ThorTrading.services.MarketOpenCapture.check_for_market_opens_and_capture()

    That function should:
      - Run one capture/evaluation cycle
      - Return a sleep interval in seconds before next check
    """
    logger.info("🌎 Market Open Capture Supervisor: starting...")

    try:
        from ThorTrading.services.MarketOpenCapture import (
            check_for_market_opens_and_capture,
        )

        while True:
            try:
                interval = check_for_market_opens_and_capture()
                logger.debug("💓 [Market Open Capture] waiting for next open...")
            except Exception:
                logger.exception(
                    "❌ Market Open Capture crashed — restarting in 5 seconds..."
                )
                interval = 5
            time.sleep(interval)

    except Exception:
        logger.exception("❌ Failed to initialize Market Open Capture Supervisor")


# =====================================================================
#  52-WEEK EXTREMES SUPERVISOR (folded into stack)
# =====================================================================
def start_52w_supervisor_wrapper():
    """
    Wrapper for the 52-week extremes supervisor.

    The underlying module already manages its own internal supervisor thread
    and has guards against duplicate starts, so we just call it once.
    """
    logger.info("📈 52-week supervisor (stack) starting...")

    try:
        from ThorTrading.services.Week52Supervisor import start_52w_monitor_supervisor

        start_52w_monitor_supervisor()
        logger.info("📈 52-week supervisor started from stack.")
    except Exception:
        logger.exception("❌ Failed to start 52-week supervisor from stack")


# =====================================================================
#  PRE-OPEN BACKTEST SUPERVISOR (folded into stack)
# =====================================================================
def start_preopen_backtest_supervisor_wrapper():
    """
    Wrapper for the Pre-open Backtest supervisor.

    As with 52w, the underlying module manages its own loop and state,
    so we just invoke its start function once.
    """
    logger.info("⏰ Pre-open backtest supervisor (stack) starting...")

    try:
        from ThorTrading.services.PreOpenBacktestSupervisor import (
            start_preopen_backtest_supervisor,
        )

        start_preopen_backtest_supervisor()
        logger.info("⏰ Pre-open backtest supervisor started from stack.")
    except Exception:
        logger.exception("❌ Failed to start Pre-open backtest supervisor from stack")


# =====================================================================
#  MASTER STACK — starts ALL supervisors
# =====================================================================
def start_thor_background_stack(force: bool = False):
    """
    Safely starts all background supervisors for Thor.

    Protects against:
      • Multiple launches (autoreload duplicates)
      • Running during management commands like migrate/test
      • Running in the wrong (non-main) runserver process
    Args:
        force: When True, bypasses the manage.py/RUN_MAIN guards so the
               stack can be launched from a dedicated worker process.
    """

    # Prevent duplicate startup in the same process
    if getattr(start_thor_background_stack, "_started", False):
        logger.info("🟡 Thor background stack already started — skipping.")
        return

    # Skip for management commands that should NOT launch background tasks
    if not force and "manage.py" in os.path.basename(sys.argv[0]):
        mgmt_cmds = {
            "migrate",
            "makemigrations",
            "collectstatic",
            "shell",
            "createsuperuser",
            "test",
        }
        if any(cmd in sys.argv for cmd in mgmt_cmds):
            logger.info("⏭️ Skipping Thor stack during management command.")
            return

    # Avoid launching from Django's autoreload parent
    if not force and os.environ.get("RUN_MAIN") != "true":
        logger.info("⏭️ Not main thread — skipping background tasks.")
        return

    # Mark as started for this process
    start_thor_background_stack._started = True

    logger.info("🚀 Starting Thor Background Stack now%s...", " (forced)" if force else "")

    # ----------------------------------------
    # 1. EXCEL POLLER
    # ----------------------------------------
    if os.environ.get("THOR_ENABLE_EXCEL_POLLER", "0") == "1":
        try:
            t1 = threading.Thread(
                target=start_excel_poller_supervisor,
                name="ExcelPollerSupervisor",
                daemon=True,
            )
            t1.start()
            logger.info("📄 Excel Poller Supervisor started.")
        except Exception:
            logger.exception("❌ Failed to start Excel Poller Supervisor")
    else:
        logger.info("📄 Skipping Excel Poller Supervisor (THOR_ENABLE_EXCEL_POLLER!=1).")

    # ----------------------------------------
    # 2. MARKET OPEN GRADER
    # ----------------------------------------
    if GLOBAL_TIMER_ENABLED:
        logger.info("📊 Global timer mode enabled — skipping legacy Market Open Grader supervisor.")
    else:
        try:
            t2 = threading.Thread(
                target=start_market_open_grader_supervisor,
                name="MarketOpenGraderSupervisor",
                daemon=True,
            )
            t2.start()
            logger.info("📊 Market Open Grader Supervisor started.")
        except Exception:
            logger.exception("❌ Failed to start Market Open Grader Supervisor")

    # ----------------------------------------
    # 3. MARKET OPEN CAPTURE SUPERVISOR
    # ----------------------------------------
    try:
        t3 = threading.Thread(
            target=start_market_open_capture_supervisor_wrapper,
            name="MarketOpenCaptureSupervisor",
            daemon=True,
        )
        t3.start()
        logger.info("🌎 Market Open Capture Supervisor started.")
    except Exception:
        logger.exception("❌ Failed to start Market Open Capture Supervisor")

    # ----------------------------------------
    # 4. 52-WEEK EXTREMES SUPERVISOR
    # ----------------------------------------
    if GLOBAL_TIMER_ENABLED:
        logger.info("📈 Global timer mode enabled — skipping legacy 52-week supervisor thread.")
    else:
        try:
            t4 = threading.Thread(
                target=start_52w_supervisor_wrapper,
                name="Week52Supervisor",
                daemon=True,
            )
            t4.start()
            logger.info("📈 52-week Supervisor thread started.")
        except Exception:
            logger.exception("❌ Failed to start 52-week Supervisor thread")

    # ----------------------------------------
    # 5. PRE-OPEN BACKTEST SUPERVISOR
    # ----------------------------------------
    try:
        t5 = threading.Thread(
            target=start_preopen_backtest_supervisor_wrapper,
            name="PreOpenBacktestSupervisor",
            daemon=True,
        )
        t5.start()
        logger.info("⏰ Pre-open Backtest Supervisor thread started.")
    except Exception:
        logger.exception("❌ Failed to start Pre-open Backtest Supervisor thread")

    logger.info("🚀 Thor Background Stack initialized.")


# =====================================================================
#  STOP (future expansion)
# =====================================================================
def stop_thor_background_stack():
    logger.info("🛑 Thor Background Stack stop requested (not implemented).")

