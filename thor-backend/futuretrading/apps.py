"""
FutureTrading AppConfig

What this file does:
- Registers the `FutureTrading` Django app configuration.
- Uses the AppConfig `ready()` hook to start background services that should
    run alongside the Django process.

Currently started service:
- 52-Week Extremes Monitor: A lightweight background thread that reads the
    latest quotes from Redis and updates `Rolling52WeekStats` whenever new
    highs/lows are observed. This keeps the 52-week stats fresh in real time
    without requiring a separate terminal.

Operational notes:
- The monitor is guarded by a singleton to avoid duplicate starts under
    Django’s autoreloader.
- You can disable it via `FUTURETRADING_ENABLE_52W_MONITOR=0` (env or settings).
- You can adjust the interval via `FUTURETRADING_52W_MONITOR_INTERVAL` (seconds).
"""

from django.apps import AppConfig


class FuturetradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FutureTrading'

    def ready(self):
        """Start FutureTrading background services when Django app registry is ready.

        - Starts the 52-week extremes monitor in the background.
        - If startup fails, logs the exception but does not block Django.
        """
        try:
            from FutureTrading.services.Week52Monitor import start_52w_monitor_supervisor
            start_52w_monitor_supervisor()
        except Exception:
            # Avoid breaking Django startup if optional service fails
            import logging
            logging.getLogger(__name__).exception("Failed to start 52w supervisor")
