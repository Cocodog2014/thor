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
        from GlobalMarkets.services.leader_lock import LeaderLock

        # Leader lock for production (Gunicorn/multi-worker)
        # In dev, can be disabled via THOR_DISABLE_LEADER_LOCK=1 for smoother experience
        disable_lock = os.environ.get("THOR_DISABLE_LEADER_LOCK", "0") == "1"
        
        lock = None
        if not disable_lock:
            lock = LeaderLock(key="thor:leader:heartbeat", ttl_seconds=30)
            if not lock.acquire(blocking=False, timeout=0):
                logger.info("🔒 Heartbeat skipped (leader lock held by another worker)")
                return
            logger.info("🔓 Heartbeat leader lock acquired")
        else:
            logger.info("🔓 Leader lock disabled (dev mode)")

        # Build registry once and register all jobs
        registry = JobRegistry()
        register_all_jobs(registry)
        
        # Safer job list logging (handles JobEntry wrapper or direct jobs)
        try:
            job_names = [entry.job.name for entry in registry.jobs]
        except (AttributeError, TypeError):
            try:
                job_names = [j.name for j in registry.jobs]
            except Exception:
                job_names = ["<unable to list jobs>"]
        logger.info("✅ Jobs registered: %s", job_names)

        def tick_seconds_fn(context):
            # FAST when any control markets are open, SLOW otherwise
            return 1.0 if has_active_markets() else 120.0

        try:
            # Get channel layer for WebSocket broadcasting (shadow mode)
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            
            logger.info("💓 Heartbeat starting (single scheduler)...")
            # run_heartbeat loops forever and renews lock each tick (if lock is enabled)
            # Only exits on stop_event, lock renewal failure, or unrecoverable error
            run_heartbeat(
                registry=registry,
                tick_seconds_fn=tick_seconds_fn,
                leader_lock=lock,
                channel_layer=channel_layer  # Shadow mode: broadcast to WebSocket clients
            )
            
            # If we reach here, it's an abnormal exit (shouldn't happen)
            logger.error("⚠️ Heartbeat exited unexpectedly")
        except Exception:
            logger.exception("❌ Heartbeat crashed with unhandled exception")
        finally:
            if lock:
                lock.release()
                logger.info("🔓 Heartbeat leader lock released")

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
