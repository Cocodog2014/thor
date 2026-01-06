from django.apps import AppConfig


class InstrumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Instruments"
    verbose_name = "Instruments"

    def ready(self):
        # Register subscription → Redis control-plane bridge.
        from . import schwab_subscription_signals  # noqa: F401

