from django.apps import AppConfig
import sys
import os
import logging


class GlobalMarketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GlobalMarkets'
    verbose_name = 'Global Markets'

    def ready(self):
        """Import signals; legacy monitor startup removed in favor of heartbeat."""
        import GlobalMarkets.signals  # noqa: F401 side-effect import
        # Track active markets in Redis for heartbeat cadence decisions
        try:
            import GlobalMarkets.services.active_markets  # noqa: F401 side-effect import
        except Exception:
            logging.getLogger(__name__).warning("Active markets tracker failed to import", exc_info=True)
