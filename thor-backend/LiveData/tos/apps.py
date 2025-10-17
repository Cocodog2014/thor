from django.apps import AppConfig


class TosConfig(AppConfig):
    """
    Thinkorswim real-time streaming integration.
    
    Stateless app - no models, just WebSocket streaming to Redis.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LiveData.tos'
    label = 'TOSFeed'
    verbose_name = 'Thinkorswim Streaming'
    
    def ready(self):
        """Called when Django starts up."""
        pass
