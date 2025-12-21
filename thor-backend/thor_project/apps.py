import logging
import sys

from django.apps import AppConfig


class ThorProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "thor_project"
    verbose_name = "Thor Platform"

    def ready(self):
        """Start the realtime heartbeat stack once per process."""
        from thor_project.realtime.runtime import start_realtime

        logger = logging.getLogger(__name__)
        argv = sys.argv or []

        # Let start_realtime handle RUN_MAIN and management guards; we just call it.
        try:
            logger.info("🔥 Thor platform ready: initializing realtime stack (platform app)...")
            start_realtime()
            logger.info("🚀 Thor realtime stack started (platform app).")
        except Exception:
            logger.exception("❌ Failed to start Thor realtime stack (platform app)")