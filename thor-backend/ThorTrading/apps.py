import os

from django.apps import AppConfig


class ThorTradingConfig(AppConfig):
    """Application config keeps legacy DB label but new module path."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ThorTrading"
    verbose_name = "Thor Trading"

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
            from ThorTrading import globalmarkets_hooks  # noqa: F401
            logger.info("📡 ThorTrading GlobalMarkets hooks registered.")

            def _bootstrap_hooks():
                time.sleep(1.0)
                try:
                    globalmarkets_hooks.bootstrap_open_markets()
                except Exception:
                    logger.exception("❌ Failed to bootstrap ThorTrading workers for open markets")

            threading.Thread(
                target=_bootstrap_hooks,
                name="ThorGlobalTimerBootstrap",
                daemon=True,
            ).start()
        except Exception:
            logger.exception("❌ Failed to import ThorTrading GlobalMarkets hooks")

        # Allow disabling the automatic stack in specific processes (e.g., web)
        auto_start = os.environ.get("THOR_STACK_AUTO_START", "1").lower() not in {"0", "false", "no"}
        if not auto_start:
            logger.info("⏭️ THOR_STACK_AUTO_START disabled — background stack will not auto-start in this process.")
            return

        try:
            from ThorTrading.services.stack_start import start_thor_background_stack
        except Exception:
            logger.exception("❌ Failed to import Thor background stack")
            return

        def _delayed_start():
            time.sleep(1.0)
            try:
                logger.info("🔥 ThorTrading app ready: initializing background stack (delayed)...")
                start_thor_background_stack()
                logger.info("🚀 Thor master stack started successfully.")
            except Exception:
                logger.exception("❌ Failed to start Thor master stack")

        threading.Thread(
            target=_delayed_start,
            name="ThorStackDelayedStart",
            daemon=True,
        ).start()

