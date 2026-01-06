from django.apps import AppConfig


def _signals_enabled() -> bool:
    # Settings is safe to import during AppConfig.ready()
    from django.conf import settings

    return bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False))


class InstrumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Instruments"
    verbose_name = "Instruments"

    def ready(self):
        # Default: keep signals OFF. The API/admin paths publish a single authoritative set.
        # If explicitly enabled, register watchlist → Redis control-plane bridge.
        if _signals_enabled():
            from . import schwab_subscription_signals  # noqa: F401

