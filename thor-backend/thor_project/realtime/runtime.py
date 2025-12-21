"""Runtime wiring for the realtime heartbeat stack."""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

from core.infra.jobs import JobRegistry

from thor_project.realtime.engine import run_heartbeat
from thor_project.realtime.leader_lock import LeaderLock
from thor_project.realtime.registry import register_jobs

logger = logging.getLogger(__name__)


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

    def _start_heartbeat():
        from channels.layers import get_channel_layer

        disable_lock = os.environ.get("THOR_DISABLE_LEADER_LOCK", "0") == "1"

        lock = None
        if not disable_lock:
            lock = LeaderLock(key="thor:leader:heartbeat", ttl_seconds=5)
            if not lock.acquire(blocking=False, timeout=0):
                logger.info("🔒 Heartbeat skipped (leader lock held by another worker)")
                return
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

            logger.info("💓 Heartbeat starting (single scheduler)...")
            run_heartbeat(
                registry=registry,
                tick_seconds_fn=tick_seconds_fn,
                leader_lock=lock,
                channel_layer=channel_layer,
            )

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
            name="ThorRealtimeHeartbeat",
            daemon=True,
        )
        t.start()
        logger.info("💓 Realtime heartbeat thread started.")
    except Exception:
        logger.exception("❌ Failed to start realtime heartbeat thread")

    logger.info("🚀 Thor Realtime stack initialized.")
