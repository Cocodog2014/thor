from django.apps import AppConfig


class GlobalMarketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GlobalMarkets'
    verbose_name = 'Global Markets'
    
    def ready(self):
        """Import signals when app is ready"""
        import GlobalMarkets.signals
