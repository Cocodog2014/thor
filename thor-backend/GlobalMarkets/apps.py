from django.apps import AppConfig
import os
import logging


logger = logging.getLogger(__name__)


class GlobalMarketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GlobalMarkets'
    verbose_name = 'Global Markets'

    def ready(self):
        """
        App initialization hooks.

        - Imports signals
        - Registers active market tracking (Redis-backed)
        - No background threads or timers started here
        """

        # Prevent double-execution during autoreload / ASGI workers
        if os.environ.get("GLOBAL_MARKETS_READY") == "1":
            return
        os.environ["GLOBAL_MARKETS_READY"] = "1"

        # Signals
        import GlobalMarkets.signals  # noqa: F401 side-effect import

        # Active markets tracker (used by heartbeat cadence logic)
        try:
            import GlobalMarkets.services.active_markets  # noqa: F401 side-effect import
        except Exception:
            logger.warning(
                "Active markets tracker failed to import",
                exc_info=True,
            )
