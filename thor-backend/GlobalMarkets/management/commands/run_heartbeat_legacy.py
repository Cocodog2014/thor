"""
Management command to run the unified heartbeat scheduler.

✅ COMPLIANT WITH "ONE TIMER" RULE:
- NO while True loops
- NO time.sleep polling
- NO tick selection logic here (no tick_seconds_fn)
- This command only boots the single realtime heartbeat loop.

Operational notes (why this file matters):
- Forces THOR_SCHEDULER_MODE="heartbeat" so old schedulers/supervisors never start.
- Optionally grabs a leader lock to prevent two heartbeat workers from running.
- Builds the job registry via register_jobs(registry) from the realtime registry.
- Creates HeartbeatContext and optional channel_layer so jobs can broadcast ticks.
- Invokes the single realtime loop thor_project.realtime.engine.run_heartbeat(...).
- This is the Django entrypoint; the continuous loop lives only here.

All scheduling policy lives in thor_project/realtime (engine/runtime).
"""
import logging
import os
import signal
import sys
import threading

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the unified heartbeat scheduler (single realtime engine)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tick",
            type=float,
            default=1.0,
            help="Heartbeat tick in seconds (default: 1.0)",
        )
        parser.add_argument(
            "--no-lock",
            action="store_true",
            help="Skip leader lock (dev only; not safe for multi-worker)",
        )

    def handle(self, *args, **options):
        tick = float(options.get("tick", 1.0))
        use_lock = not bool(options.get("no_lock", False))

        # Ensure legacy supervisors do not start
        os.environ["THOR_SCHEDULER_MODE"] = "heartbeat"

        self.stdout.write(self.style.SUCCESS("🚀 Heartbeat scheduler starting"))
        self.stdout.write(f"   Tick: {tick}s")
        self.stdout.write(f"   Leader lock: {'enabled' if use_lock else 'disabled'}")

        lock = None
        if use_lock:
            from thor_project.realtime.leader_lock import LeaderLock

            lock = LeaderLock(key="globalmarkets:leader:heartbeat", ttl_seconds=30)
            if not lock.acquire(blocking=True, timeout=10):
                self.stdout.write(self.style.ERROR("❌ Failed to acquire leader lock; exiting"))
                sys.exit(1)
            self.stdout.write(self.style.SUCCESS("✓ Leader lock acquired"))

        try:
            self._run_heartbeat(tick)
        finally:
            if lock:
                lock.release()
                self.stdout.write("Leader lock released")

    def _run_heartbeat(self, tick: float) -> None:
        from core.infra.jobs import JobRegistry
        from thor_project.realtime.engine import HeartbeatContext, run_heartbeat
        from thor_project.realtime.registry import register_jobs

        # Single registry (source of truth for all jobs)
        registry = JobRegistry()
        job_names = register_jobs(registry) or []
        logger.info("Heartbeat ready with %d jobs: %s", len(registry.jobs), job_names)

        # Graceful shutdown on SIGTERM/SIGINT
        stop_event = threading.Event()

        def _on_signal(sig, frame):
            logger.info("Received signal %s; stopping heartbeat", sig)
            stop_event.set()

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)

        # Heartbeat context
        ctx = HeartbeatContext(
            logger=logger,
            shared_state={"last_run": {}},
            stop_event=stop_event,
        )

        # Channel layer (optional) for WebSocket broadcasting
        try:
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
        except Exception:
            logger.warning("Could not get channel layer for WebSocket broadcasting")
            channel_layer = None

        # Run the single realtime heartbeat loop
        try:
            run_heartbeat(
                registry=registry,
                tick_seconds=tick,
                ctx=ctx,
                channel_layer=channel_layer,
            )
        except KeyboardInterrupt:
            logger.info("Heartbeat interrupted")
        finally:
            logger.info("Heartbeat stopped")
