# FutureTrading/services/stack_start.py

import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)


# =====================================================================
#  EXCEL → REDIS POLLER SUPERVISOR
# =====================================================================
def start_excel_poller_supervisor():
    """
    Supervisor wrapper for the existing TOS Excel poller.
    Uses the Django management command: poll_tos_excel
    """
    logger.info("📄 Excel Poller Supervisor: starting...")

    try:
        # NOTE: poll_tos_excel lives in LiveData, not FutureTrading
        from LiveData.management.commands.poll_tos_excel import Command

        poller = Command()

        while True:
            try:
                logger.info("🚀 Excel Poller: running...")
                # This will block and poll Excel → Redis
                poller.handle()
                logger.debug("💓 [Excel Poller] alive")
            except Exception:
                logger.exception("❌ Excel Poller crashed — restarting in 3 seconds...")
                time.sleep(3)

    except Exception:
        logger.exception("❌ Failed to initialize Excel Poller Supervisor")


# =====================================================================
#  MARKET OPEN GRADER SUPERVISOR
# =====================================================================
def start_market_open_grader_supervisor():
    """
    Supervisor wrapper for the existing Market Open Grader command.
    Normally run via:
        python manage.py start_market_grader --interval 0.5

    We simulate that call and auto-restart on crash.
    """
    logger.info("📊 Market Open Grader Supervisor: starting...")

    try:
        from FutureTrading.management.commands.start_market_grader import Command
        grader = Command()

        while True:
            try:
                logger.info("🚀 Market Open Grader: running...")
                # Provide interval, since the command expects options['interval']
                grader.handle(interval=0.5)
                logger.debug("💓 [Market Open Grader] alive")
            except Exception:
                logger.exception("❌ Market Open Grader crashed — restarting in 3 seconds...")
                time.sleep(3)

    except Exception:
        logger.exception("❌ Failed to initialize Market Open Grader Supervisor")


# =====================================================================
#  INTRADAY SUPERVISOR
# =====================================================================
    
# =====================================================================
#  MARKET OPEN CAPTURE SUPERVISOR
# =====================================================================
def start_market_open_capture_supervisor_wrapper():
    """
    Supervisor wrapper for the Market Open Capture logic.
    Auto-restarts and paces itself using returned sleep intervals.
    """
    logger.info("🌎 Market Open Capture Supervisor: starting...")

    try:
        from FutureTrading.services.MarketOpenCapture import check_for_market_opens_and_capture

        while True:
            try:
                interval = check_for_market_opens_and_capture()
                logger.debug("💓 [Market Open Capture] waiting for next open...")
            except Exception:
                logger.exception("❌ Market Open Capture crashed — restarting in 5 seconds...")
                interval = 5
            time.sleep(interval)

    except Exception:
        logger.exception("❌ Failed to initialize Market Open Capture Supervisor")


# =====================================================================
#  MASTER STACK — starts ALL supervisors (Excel, Grader, Capture)
# =====================================================================
def start_thor_background_stack():
    """
    Safely starts all background supervisors for Thor.
    Prevents:
        • Multiple launches (autoreload duplicates)
        • Starting during migrations / admin commands
        • Starting outside Django runserver main thread
    """

    # Prevent duplicate startup
    if getattr(start_thor_background_stack, "_started", False):
        logger.info("🟡 Thor background stack already started — skipping.")
        return

    # Skip for management commands that should NOT launch background tasks
    if "manage.py" in os.path.basename(sys.argv[0]):
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

    # Skip duplicate startup from Django's autoreload parent process
    if os.environ.get("RUN_MAIN") != "true":
        logger.info("⏭️ Not main thread — skipping background tasks.")
        return

    # Mark stack as started
    start_thor_background_stack._started = True

    logger.info("🚀 Starting Thor Background Stack now...")

    # ----------------------------------------
    # 1. EXCEL POLLER
    # ----------------------------------------
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

    # ----------------------------------------
    # 2. MARKET OPEN GRADER
    # ----------------------------------------
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

    logger.info("🚀 Thor Background Stack initialized.")


# =====================================================================
#  STOP (future expansion)
# =====================================================================
def stop_thor_background_stack():
    logger.info("🛑 Thor Background Stack stop requested (not implemented).")
