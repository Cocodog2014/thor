from django.apps import AppConfig


class FuturetradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "FutureTrading"

    def ready(self):
        """
        Kick off Thor background stack via a short delayed thread.

        This prevents database access during app initialization and ensures
        all supervisors are orchestrated by services.stack_start.
        """
        import logging
        import threading
        import time

        logger = logging.getLogger(__name__)

        try:
            from FutureTrading.services.stack_start import start_thor_background_stack
        except Exception:
            logger.exception("❌ Failed to import Thor background stack")
            return

        def _delayed_start():
            time.sleep(1.0)
            try:
                logger.info("🔥 FutureTrading app ready: initializing background stack (delayed)...")
                start_thor_background_stack()
                logger.info("🚀 Thor master stack started successfully.")
            except Exception:
                logger.exception("❌ Failed to start Thor master stack")

        threading.Thread(
            target=_delayed_start,
            name="ThorStackDelayedStart",
            daemon=True,
        ).start()

