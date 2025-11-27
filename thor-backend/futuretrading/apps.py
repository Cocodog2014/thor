from django.apps import AppConfig
import logging
import threading


class FuturetradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FutureTrading'

    _initialized = False  # Prevent Django from starting supervisors twice

    def ready(self):
        """
        Start all FutureTrading background services when Django loads.

        This now does THREE things:

        1. Starts master stack controller: stack_start.py
        2. Starts 52-week monitor supervisor
        3. Starts Pre-open backtest supervisor

        Nothing blocks Django startup — everything runs in threads.
        """
        if self._initialized:
            return  # Prevent duplicate startup
        self._initialized = True

        logger = logging.getLogger(__name__)
        logger.info("🔥 FutureTrading app ready: initializing background stack...")

        # ------------------------------------------------------
        # 1. MASTER STACK (the new unified launcher)
        # ------------------------------------------------------
        try:
            from FutureTrading.services.stack_start import start_thor_background_stack

            threading.Thread(
                target=start_thor_background_stack,
                name="ThorMasterStack",
                daemon=True
            ).start()

            logger.info("🚀 Thor master stack started successfully.")
        except Exception:
            logger.exception("❌ Failed to start Thor master stack")

        # ------------------------------------------------------
        # 2. 52-WEEK SUPERVISOR (legacy)
        # ------------------------------------------------------
        try:
            from FutureTrading.services.Week52Superviror import start_52w_monitor_supervisor

            threading.Thread(
                target=start_52w_monitor_supervisor,
                name="Supervisor52W",
                daemon=True
            ).start()

            logger.info("📈 52-week supervisor started.")
        except Exception:
            logger.exception("❌ Failed to start 52-week supervisor")

        # ------------------------------------------------------
        # 3. PRE-OPEN BACKTEST SUPERVISOR
        # ------------------------------------------------------
        try:
            from FutureTrading.services.PreOpenBacktestSupervisor import (
                start_preopen_backtest_supervisor
            )

            threading.Thread(
                target=start_preopen_backtest_supervisor,
                name="PreOpenSupervisor",
                daemon=True
            ).start()

            logger.info("⏰ Pre-open backtest supervisor started.")
        except Exception:
            logger.exception("❌ Failed to start pre-open backtest supervisor")

