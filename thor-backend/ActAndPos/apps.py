from django.apps import AppConfig


class ActandposConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ActAndPos"
    verbose_name = "Accounts and Positions"

    def ready(self):  # pragma: no cover
        # NOTE: seed_default_paper_account was removed with legacy models
        # If needed, move seeding logic to management command or signal
        
        # Register split-domain models (scaffolding).
        # Importing here keeps existing ActAndPos models untouched while we
        # build paper/live side-by-side.
        from .paper import models as _paper_models  # noqa: F401
        from .live import models as _live_models  # noqa: F401
