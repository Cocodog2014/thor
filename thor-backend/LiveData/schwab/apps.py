from django.apps import AppConfig


class SchwabConfig(AppConfig):
    """
    Schwab OAuth and Trading API integration.
    
    Important: Uses label='SchwabLiveData' to maintain compatibility
    with existing database migrations from the old SchwabLiveData app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LiveData.schwab'
    label = 'SchwabLiveData'  # ← Keeps existing DB tables intact!
    verbose_name = 'Schwab OAuth & Trading API'
    
    def ready(self):
        """Called when Django starts up."""
        # Register model signals (Admin add/edit/delete should update streaming instantly)
        from . import signals  # noqa: F401
