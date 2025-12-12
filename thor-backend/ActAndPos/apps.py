from django.apps import AppConfig


class ActandposConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ActAndPos"
    verbose_name = "Accounts and Positions"

    def ready(self):  # pragma: no cover
        from . import seed_default_paper_account  # noqa: F401
