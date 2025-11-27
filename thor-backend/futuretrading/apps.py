from django.apps import AppConfig


class FuturetradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FutureTrading'

    def ready(self):
        """Start FutureTrading background services when Django app registry is ready.

        - Starts the 52-week extremes monitor in the background.
        - Starts the pre-open backtest supervisor.
        - If startup fails, logs the exception but does not block Django.
        """
        import logging
        logger = logging.getLogger(__name__)

        # 52-week extremes supervisor
        try:
            from FutureTrading.services.Week52Superviror import start_52w_monitor_supervisor
            start_52w_monitor_supervisor()
        except Exception:
            logger.exception("Failed to start 52w supervisor")

        # Pre-open backtest supervisor (T-minus 60s)
        try:
            from FutureTrading.services.PreOpenBacktestSupervisor import (
                start_preopen_backtest_supervisor,
            )
            start_preopen_backtest_supervisor()
        except Exception:
            logger.exception("Failed to start pre-open backtest supervisor")
