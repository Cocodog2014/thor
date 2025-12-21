"""Runtime wiring for the realtime heartbeat stack."""
from __future__ import annotations

import atexit
import logging
import os
import signal
import sys
import threading
import time

from core.infra.jobs import JobRegistry

from thor_project.realtime.engine import HeartbeatContext, run_heartbeat
from thor_project.realtime.leader_lock import LeaderLock
from thor_project.realtime.registry import register_jobs

logger = logging.getLogger(__name__)

# Global state for realtime thread and lock
_stop_event = threading.Event()
_thread: threading.Thread | None = None
_lock: LeaderLock | None = None


def _truthy_env(name: str, default: str = "0") -> bool:
    value = os.environ.get(name, default)
    return str(value).lower() not in {"0", "false", "no", ""}


def start_realtime(force: bool = False) -> None:
    """Start the realtime heartbeat in a background thread (single scheduler)."""

    if getattr(start_realtime, "_started", False):
        logger.info("🟡 Realtime heartbeat already started — skipping.")
        return

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
            logger.info("⏭️ Skipping realtime heartbeat during management command.")
            return

    if not force and os.environ.get("RUN_MAIN") != "true":
        logger.info("⏭️ Not main runserver process — skipping realtime heartbeat.")
        return

    start_realtime._started = True

    os.environ.setdefault("THOR_SCHEDULER_MODE", "heartbeat")
    os.environ.setdefault("HEARTBEAT_ENABLED", "1")

    logger.info("🚀 Starting realtime heartbeat stack now%s...", " (forced)" if force else "")

    def _request_shutdown(reason: str):
        logger.info("🛑 Realtime shutdown requested (%s)", reason)
        _stop_event.set()

    def _stop_thread():
        global _thread
        if _thread and _thread.is_alive():
            _thread.join(timeout=5)
            if _thread.is_alive():
                logger.warning("⚠️ Heartbeat thread did not exit within timeout")
        _thread = None

    def _install_shutdown_hooks_once():
        if getattr(start_realtime, "_hooks_installed", False):
            return
        start_realtime._hooks_installed = True

        atexit.register(lambda: _request_shutdown("atexit"))

        prev_sigint = signal.getsignal(signal.SIGINT)
        prev_sigterm = signal.getsignal(signal.SIGTERM)

        def _handler(signum, frame):  # type: ignore[override]
            _request_shutdown(f"signal {signum}")

            prev = prev_sigint if signum == signal.SIGINT else prev_sigterm
            if callable(prev):
                return prev(signum, frame)

            if signum == signal.SIGINT:
                raise KeyboardInterrupt

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except Exception:
            # Some signals may not be available in all environments
            pass

    _install_shutdown_hooks_once()

    def _start_heartbeat():
        import time as _time
        from django.apps import apps as django_apps

        # Ensure Django finished initializing before any ORM access inside heartbeat jobs
        while not django_apps.ready:
            _time.sleep(0.05)

        from channels.layers import get_channel_layer
        from thor_project.realtime.engine import HeartbeatContext

        global _lock

        disable_lock = os.environ.get("THOR_DISABLE_LEADER_LOCK", "0") == "1"

        lock = None
        if not disable_lock:
            lock = LeaderLock(key="thor:leader:heartbeat", ttl_seconds=30)
            if not lock.acquire(blocking=False, timeout=0):
                logger.info("🔒 Heartbeat skipped (leader lock held by another worker)")
                return
            _lock = lock
            logger.info("🔓 Heartbeat leader lock acquired")
        else:
            logger.info("🔓 Leader lock disabled (dev mode)")

        registry = JobRegistry()
        job_names = register_jobs(registry) or []
        logger.info("✅ Jobs registered: %s", job_names)

        def tick_seconds_fn(context):
            return 1.0

        try:
            channel_layer = get_channel_layer()

            ctx = HeartbeatContext(
                logger=logging.getLogger("heartbeat"),
                shared_state={},
                stop_event=_stop_event,
                channel_layer=channel_layer,
            )

            logger.info("💓 Heartbeat starting (single scheduler)...")
            run_heartbeat(
                registry=registry,
                tick_seconds_fn=tick_seconds_fn,
                leader_lock=lock,
                channel_layer=channel_layer,
                ctx=ctx,
            )
            logger.info("🛑 Heartbeat exited cleanly")
        except Exception:
            logger.exception("❌ Heartbeat crashed with unhandled exception")
        finally:
            if lock:
                lock.release()
                logger.info("🔓 Heartbeat leader lock released")
            _lock = None

    try:
        global _thread
        _stop_event.clear()

        t = threading.Thread(
            target=_start_heartbeat,
            name="ThorRealtimeHeartbeat",
            daemon=True,
        )
        t.start()
        _thread = t
        logger.info("💓 Realtime heartbeat thread started.")
    except Exception:
        logger.exception("❌ Failed to start realtime heartbeat thread")

    logger.info("🚀 Thor Realtime stack initialized.")
