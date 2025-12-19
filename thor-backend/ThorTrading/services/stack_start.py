# ThorTrading/services/stack_start.py

import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)


def _truthy_env(name: str, default: str = "0") -> bool:
    value = os.environ.get(name, default)
    return str(value).lower() not in {"0", "false", "no", ""}


def start_thor_background_stack(force: bool = False):
    """
    Starts Thor background services in-process for runserver dev.

    Single scheduler for market supervisors:
      - Heartbeat loop dispatches Jobs (intraday, 24h, session vol, metrics, vwap, 52w, preopen backtest, etc.)

    Guards:
      - Avoid autoreload duplicates
      - Avoid running for management commands
      - (Later) add Redis leader lock for multi-worker production
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
        logger.info("⏭️ Not main runserver process — skipping background tasks.")
        return

    start_thor_background_stack._started = True

    # Ensure legacy supervisors don’t accidentally start
    os.environ.setdefault("THOR_SCHEDULER_MODE", "heartbeat")
    os.environ.setdefault("HEARTBEAT_ENABLED", "1")

    logger.info("🚀 Starting Thor Background Stack now%s...", " (forced)" if force else "")

    def _start_heartbeat():
        from core.infra.jobs import JobRegistry
        from GlobalMarkets.services.heartbeat import run_heartbeat
        from ThorTrading.services.supervisors.register_jobs import register_all_jobs
        from GlobalMarkets.services.active_markets import has_active_markets

        while True:
            try:
                registry = JobRegistry()
                register_all_jobs(registry)

                def tick_seconds_fn(context):
                    # FAST when any control markets are open, SLOW otherwise
                    return 1.0 if has_active_markets() else 120.0

                logger.info("💓 Heartbeat starting (single scheduler)...")
                run_heartbeat(registry=registry, tick_seconds_fn=tick_seconds_fn)

                # If run_heartbeat returns, treat as abnormal exit and restart
                logger.warning("⚠️ Heartbeat exited unexpectedly — restarting in 5s...")
            except Exception:
                logger.exception("❌ Heartbeat crashed — restarting in 5s...")

            time.sleep(5)

    try:
        t = threading.Thread(
            target=_start_heartbeat,
            name="ThorHeartbeat",
            daemon=True,
        )
        t.start()
        logger.info("💓 Heartbeat thread started.")
    except Exception:
        logger.exception("❌ Failed to start Heartbeat thread")

    logger.info("🚀 Thor Background Stack initialized.")


def stop_thor_background_stack():
    logger.info("🛑 Thor Background Stack stop requested (not implemented).")
