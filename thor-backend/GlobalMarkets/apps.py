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
        """
        import GlobalMarkets.signals  # noqa: F401 side-effect import

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
                start_monitor()
                logging.getLogger(__name__).info("GlobalMarkets monitor started (delayed).")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "GlobalMarkets monitor did not start (suppressed): %s", e
                )

        threading.Thread(
            target=_delayed_start,
            name='GlobalMarketsMonitorStart',
            daemon=True,
        ).start()
