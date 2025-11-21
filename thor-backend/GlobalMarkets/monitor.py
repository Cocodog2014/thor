"""
Automated Market Scheduler – schedules precise open/close events per market.
Instead of polling every N seconds, we compute each market's next event time
and schedule a one-shot timer to fire exactly at that moment.

This module ONLY manages Market.status and emits Django signals.
It does NOT perform any data capture – other apps listen to signals for that.
"""
import logging
import threading
from datetime import datetime
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class MarketMonitor:
    """Event-driven scheduler that updates market status exactly at transitions."""

    def __init__(self, _unused_check_interval: int = 60):
        # Keep signature for backwards-compatibility with settings
        self.running = False
        self._lock = threading.RLock()
        self._timers: Dict[int, threading.Timer] = {}

    def start(self):
        """Initialize schedules for all control markets."""
        with self._lock:
            if self.running:
                logger.warning("Market monitor already running")
                return
            self.running = True

        # Lazy imports to avoid app registry issues
        from GlobalMarkets.models import Market

        markets = Market.objects.filter(is_active=True, is_control_market=True)
        count = 0
        for m in markets:
            try:
                self._schedule_next_event(m.id)
                count += 1
            except Exception as e:
                logger.error(f"❌ Failed to schedule {m.country}: {e}", exc_info=True)

        logger.info(f"🌍 Market Scheduler started – timers scheduled for {count} markets")

        # Immediate reconciliation so we don't wait for the next timer if a market
        # is already OPEN/CLOSED right now but DB status is stale (first-run fix).
        try:
            self._reconcile_now()
        except Exception as e:
            logger.error(f"❌ Initial reconciliation failed: {e}", exc_info=True)

    def stop(self):
        """Cancel all timers and stop scheduling."""
        with self._lock:
            self.running = False
            for market_id, t in list(self._timers.items()):
                try:
                    t.cancel()
                except Exception:
                    pass
                finally:
                    self._timers.pop(market_id, None)
        logger.info("🛑 Market Scheduler stopped")

    # --------------------
    # Scheduling internals
    # --------------------
    def _schedule_next_event(self, market_id: int):
        """Compute the next open/close event and arm a timer for it."""
        if not self.running:
            return

        from GlobalMarkets.models import Market
        market = Market.objects.get(pk=market_id)

        status_info = market.get_market_status()
        if not status_info:
            return

        seconds = max(0, int(status_info.get('seconds_to_next_event', 0)))

        # Ensure we don't schedule 0-second timers repeatedly; add a tiny buffer
        delay = max(0.5, float(seconds))

        next_event = status_info.get('next_event')  # 'open' | 'close'
        human_at = status_info.get('next_open_at') if next_event == 'open' else status_info.get('next_close_at')

        def _fire():
            try:
                self._handle_event(market_id)
            finally:
                # After handling, reschedule the next event for this market
                # We always reschedule, even if handling raised, to avoid stalls
                try:
                    self._schedule_next_event(market_id)
                except Exception as e:
                    logger.error(f"❌ Reschedule failed for market #{market_id}: {e}", exc_info=True)

        timer = threading.Timer(delay, _fire)
        timer.daemon = True
        with self._lock:
            # Cancel any existing timer for this market
            old = self._timers.get(market_id)
            if old:
                try:
                    old.cancel()
                except Exception:
                    pass
            self._timers[market_id] = timer

        logger.info(
            f"⏱️ Scheduled {market.country} next {next_event} in {int(delay)}s (at {human_at})"
        )
        timer.start()

    def _handle_event(self, market_id: int):
        """
        Execute the status transition.
        
        This method ONLY updates Market.status and logs the change.
        The post_save signal will fire and notify any listeners (e.g. FutureTrading).
        """
        from GlobalMarkets.models import Market

        try:
            market = Market.objects.get(pk=market_id)
        except Market.DoesNotExist:
            return

        # Determine target status based on real-time check
        is_open_now = market.is_market_open_now()
        target_status = 'OPEN' if is_open_now else 'CLOSED'

        if market.status == target_status:
            # No change; nothing to do
            return

        prev = market.status
        market.status = target_status
        market.save()  # This triggers post_save signal → signal handlers can capture
        logger.info(f"🔄 {market.country}: {prev} → {target_status}")

    def _reconcile_now(self):
        """
        On startup, immediately correct any status mismatches.

        This ensures that if Django starts while a market is already OPEN but the
        DB still says CLOSED, we flip it now without waiting hours for the next timer.
        
        The post_save signal will handle any capture logic via listeners.
        """
        from GlobalMarkets.models import Market

        markets = Market.objects.filter(is_active=True, is_control_market=True)
        fixed = 0
        for m in markets:
            try:
                is_open_now = m.is_market_open_now()
                target = 'OPEN' if is_open_now else 'CLOSED'
                if m.status != target:
                    prev = m.status
                    m.status = target
                    m.save()  # This triggers post_save signal → signal handlers can capture
                    fixed += 1
                    logger.info(f"🧭 Reconciled {m.country}: {prev} → {target}")
            except Exception as e:
                logger.error(f"❌ Reconcile error for {m.country}: {e}")

        if fixed:
            logger.info(f"🔧 Reconciliation completed – corrected {fixed} market(s)")
        else:
            logger.info("🔧 Reconciliation completed – no changes needed")


# Global singleton instance
_monitor_instance = None


def get_monitor():
    """Get the global monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        # Interval is unused in event-driven mode; kept for backwards-compatibility
        _ = getattr(settings, 'MARKET_MONITOR_INTERVAL', 60)
        _monitor_instance = MarketMonitor()
    return _monitor_instance


def start_monitor():
    """Start the market monitor (called from AppConfig.ready())"""
    monitor = get_monitor()
    monitor.start()


def stop_monitor():
    """Stop the market monitor"""
    monitor = get_monitor()
    monitor.stop()
