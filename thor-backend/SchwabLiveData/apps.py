from django.apps import AppConfig


class SchwablivedataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SchwabLiveData'
    verbose_name = 'Schwab Live Data Provider'
    
    def ready(self):
        """
        Called when Django starts up.
        Good place for any initialization code.
        """
        # Import any signals or startup code here if needed
        pass
