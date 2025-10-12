"""
Simplified admin interface for SchwabLiveData consumer configuration.
"""

from django.contrib import admin
from django.contrib import messages
from .simple_models import ConsumerConfiguration


@admin.register(ConsumerConfiguration)
class ConsumerConfigurationAdmin(admin.ModelAdmin):
    """Simple admin for configuring which apps get data from which providers."""
    
    list_display = (
        'app_name', 
        'primary_provider', 
        'fallback_provider',
        'is_active',
        'updated_at'
    )
    
    list_filter = ('primary_provider', 'is_active')
    
    search_fields = ('app_name', 'notes')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fields = (
        'app_name',
        'primary_provider', 
        'fallback_provider',
        'is_active',
        'notes',
        ('created_at', 'updated_at'),
    )
    
    def save_model(self, request, obj, form, change):
        """Show helpful messages when saving."""
        super().save_model(request, obj, form, change)
        
        action = "Updated" if change else "Created"
        messages.success(
            request,
            f"✅ {action} data flow: {obj.get_app_name_display()} "
            f"← {obj.get_primary_provider_display()}"
        )
        
        if obj.fallback_provider:
            messages.info(
                request,
                f"📡 Fallback configured: {obj.get_fallback_provider_display()}"
            )


# Alternative: You could also just add a simple function to your existing views
def get_consumer_provider_config(consumer_app_name):
    """
    Get the provider configuration for a consumer app.
    
    This replaces the complex routing logic with a simple lookup.
    """
    try:
        config = ConsumerConfiguration.objects.get(
            app_name=consumer_app_name,
            is_active=True
        )
        return config.provider_config
    except ConsumerConfiguration.DoesNotExist:
        # Default configuration
        return {
            'consumer': consumer_app_name,
            'primary_provider': 'excel_live',
            'fallback_provider': None,
            'is_active': True
        }