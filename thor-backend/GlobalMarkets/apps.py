from django.apps import AppConfig
import sys
import os
import logging


class GlobalMarketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GlobalMarkets'
    verbose_name = 'Global Markets'

    def ready(self):
        """Import signals and conditionally start market monitor.

        Guard against starting during migration-related commands when model
        fields may not yet exist in the database. Optional env var
        DISABLE_GLOBAL_MARKETS_MONITOR=1 prevents startup entirely.
        
        Default scheduler mode is "heartbeat" (new unified approach).
        Set THOR_SCHEDULER_MODE=legacy to use old threaded supervisors.
        """
        import GlobalMarkets.signals  # noqa: F401 side-effect import
        # Track active markets in Redis for heartbeat cadence decisions
        try:
            import GlobalMarkets.services.active_markets  # noqa: F401 side-effect import
        except Exception:
            logging.getLogger(__name__).warning("Active markets tracker failed to import", exc_info=True)

        skip_commands = {
            'makemigrations', 'migrate', 'showmigrations', 'sqlmigrate',
            'collectstatic', 'shell', 'test', 'createsuperuser', 'check',
            'diffsettings'
        }
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        if os.environ.get('DISABLE_GLOBAL_MARKETS_MONITOR', '').lower() in {'1', 'true', 'yes'}:
            return
        import threading
        import time

        def _delayed_start():
            time.sleep(1.0)
            try:
                from .monitor import start_monitor
                from GlobalMarkets.services.leader_lock import LeaderLock, set_monitor_leader_lock

                lock = LeaderLock(key="globalmarkets:leader:monitor", ttl_seconds=60)
                if not lock.acquire(blocking=False, timeout=0):
                    logging.getLogger(__name__).info("GlobalMarkets monitor skipped (leader lock held)")
                    return

                set_monitor_leader_lock(lock)
                start_monitor()
                logging.getLogger(__name__).info("GlobalMarkets monitor started (delayed, leader)")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "GlobalMarkets monitor did not start (suppressed): %s", e
                )

        threading.Thread(
            target=_delayed_start,
            name='GlobalMarketsMonitorStart',
            daemon=True,
        ).start()
