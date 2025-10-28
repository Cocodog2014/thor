from django.apps import AppConfig


class GlobalMarketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GlobalMarkets'
    verbose_name = 'Global Markets'
    
    def ready(self):
        """Import signals and start market monitor when app is ready"""
        import GlobalMarkets.signals
        
        # Start the automated market monitor in background
        # This monitors markets and triggers captures automatically
        from GlobalMarkets.monitor import start_monitor
        start_monitor()
