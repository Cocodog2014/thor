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
        fast_tick = options.get("fast_tick", 1.0)
        slow_tick = options.get("slow_tick", 60.0)
        use_lock = not options.get("no_lock", False)

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

        # Register all jobs with their default intervals
        registry = JobRegistry()

        # Market-facing jobs (run during market hours)
        from ThorTrading.services.intraday_job import IntradayJob
        from ThorTrading.services.session_volume_job import SessionVolumeJob
        from ThorTrading.services.twentyfour_hour_job import TwentyFourHourJob
        from ThorTrading.services.market_metrics_job import MarketMetricsJob
        from ThorTrading.services.closed_bars_flush_job import ClosedBarsFlushJob
        from ThorTrading.services.week52_extremes_job import Week52ExtremesJob
        from ThorTrading.services.preopen_backtest_job import PreOpenBacktestJob
        from ThorTrading.services.vwap_minute_capture_job import VwapMinuteCaptureJob

        registry.register(IntradayJob(interval_seconds=1.0))
        registry.register(SessionVolumeJob(interval_seconds=10.0))
        registry.register(TwentyFourHourJob(interval_seconds=30.0))
        registry.register(MarketMetricsJob(interval_seconds=10.0))
        registry.register(ClosedBarsFlushJob(interval_seconds=60.0))
        registry.register(Week52ExtremesJob(interval_seconds=2.0))
        registry.register(PreOpenBacktestJob(interval_seconds=30.0))
        registry.register(VwapMinuteCaptureJob(interval_seconds=60.0))

        logger.info("Registered %d jobs", len(registry.jobs))

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

        # Run the heartbeat loop
        try:
            run_heartbeat(
                registry=registry,
                tick_seconds=fast_tick,  # Default to fast; selector can change it per tick
                tick_seconds_fn=_select_tick,
                ctx=ctx,
            )
        except KeyboardInterrupt:
            logger.info("Heartbeat interrupted")
        finally:
            logger.info("Heartbeat stopped")
