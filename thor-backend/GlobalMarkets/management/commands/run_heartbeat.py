"""Management command to run the unified heartbeat scheduler.

This is the single entry point for all market-related periodic jobs:
- Intraday tick capture
- Session volume accumulation
- 24h rolling stats
- Closed bar flushing
- Market metrics
- 52-week extremes
- Pre-open backtests

Acquires a Redis leader lock to ensure only one heartbeat runs in multi-worker environments.
"""
import logging
import os
import signal
import sys
import threading

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the unified heartbeat scheduler for all market jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fast-tick",
            type=float,
            default=1.0,
            help="Heartbeat tick in seconds when markets are open (default: 1.0)",
        )
        parser.add_argument(
            "--slow-tick",
            type=float,
            default=60.0,
            help="Heartbeat tick in seconds when markets are closed (default: 60.0)",
        )
        parser.add_argument(
            "--no-lock",
            action="store_true",
            help="Skip leader lock (dev only; not safe for multi-worker)",
        )

    def handle(self, *args, **options):
        import os
        fast_tick = options.get("fast_tick", 1.0)
        slow_tick = options.get("slow_tick", 60.0)
        use_lock = not options.get("no_lock", False)

        # Set heartbeat mode so legacy supervisors don't run
        os.environ["THOR_SCHEDULER_MODE"] = "heartbeat"

        self.stdout.write(self.style.SUCCESS("🚀 Heartbeat scheduler starting"))
        self.stdout.write(f"   Fast tick: {fast_tick}s (markets open)")
        self.stdout.write(f"   Slow tick: {slow_tick}s (markets closed)")
        self.stdout.write(f"   Leader lock: {'enabled' if use_lock else 'disabled'}")

        # Acquire leader lock if requested
        lock = None
        if use_lock:
            from GlobalMarkets.services.leader_lock import LeaderLock

            lock = LeaderLock(key="globalmarkets:leader:heartbeat", ttl_seconds=30)
            if not lock.acquire(blocking=True, timeout=10):
                self.stdout.write(self.style.ERROR("❌ Failed to acquire leader lock; exiting"))
                sys.exit(1)
            self.stdout.write(self.style.SUCCESS("✓ Leader lock acquired"))

        try:
            self._run_heartbeat(fast_tick, slow_tick)
        finally:
            if lock:
                lock.release()
                self.stdout.write("Leader lock released")

    def _run_heartbeat(self, fast_tick: float, slow_tick: float) -> None:
        from core.infra.jobs import JobRegistry
        from GlobalMarkets.services.heartbeat import run_heartbeat, HeartbeatContext
        from GlobalMarkets.services.active_markets import has_active_markets
        from ThorTrading.services.supervisors.register_jobs import register_all_jobs

        # Create single registry (source of truth for all jobs)
        registry = JobRegistry()

        # Register all jobs from central location
        register_all_jobs(registry)

        logger.info("Heartbeat ready with %d jobs", len(registry.jobs))

        # Set up graceful shutdown on SIGTERM/SIGINT
        stop_event = threading.Event()

        def _on_signal(sig, frame):
            logger.info("Received signal %s; stopping heartbeat", sig)
            stop_event.set()

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)

        # Create heartbeat context
        ctx = HeartbeatContext(
            logger=logger,
            shared_state={"last_run": {}},
            stop_event=stop_event,
        )

        # Dynamic tick selector: fast when markets are open, slow when closed
        def _select_tick(context: HeartbeatContext) -> float:
            return fast_tick if has_active_markets() else slow_tick

        # Get channel layer for WebSocket broadcasting (shadow mode)
        try:
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
        except Exception:
            logger.warning("Could not get channel layer for WebSocket broadcasting")
            channel_layer = None

        # Run the heartbeat loop with the single registry
        try:
            run_heartbeat(
                registry=registry,
                tick_seconds=fast_tick,  # Default to fast; selector can change it per tick
                tick_seconds_fn=_select_tick,
                ctx=ctx,
                channel_layer=channel_layer,  # Shadow mode: broadcast to WebSocket clients
            )
        except KeyboardInterrupt:
            logger.info("Heartbeat interrupted")
        finally:
            logger.info("Heartbeat stopped")
