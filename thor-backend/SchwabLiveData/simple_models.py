"""
Simplified Consumer Configuration for SchwabLiveData Provider

This replaces the over-complicated DataFeed + FeedAssignment + ConsumerApp
with a simple direct configuration approach.
"""

from django.db import models
from django.core.exceptions import ValidationError


class DataProviderChoice(models.TextChoices):
    """Available data providers in the SchwabLiveData system."""
    EXCEL_RTD = "excel_live", "Excel Real-Time Data"
    SCHWAB_API = "schwab", "Schwab API"


class ConsumerConfiguration(models.Model):
    """Simple configuration for apps consuming SchwabLiveData."""
    
    # Which Thor app is consuming the data
    app_name = models.CharField(
        max_length=64,
        unique=True,
        choices=[
            ('futures_trading', 'Futures Trading'),
            ('stock_trading', 'Stock Trading'), 
            ('thor_frontend', 'Thor Frontend'),
            ('thor_api', 'Thor API'),
        ],
        help_text="Which Thor app will consume this data"
    )
    
    # Which data source to use
    primary_provider = models.CharField(
        max_length=20,
        choices=DataProviderChoice.choices,
        default=DataProviderChoice.EXCEL_RTD,
        help_text="Primary data source for this app"
    )
    
    # Fallback if primary fails
    fallback_provider = models.CharField(
        max_length=20,
        choices=DataProviderChoice.choices,
        blank=True,
        help_text="Fallback data source if primary fails"
    )
    
    # Simple enable/disable
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable data flow to this app"
    )
    
    # Configuration notes
    notes = models.TextField(
        blank=True,
        help_text="Configuration notes or special requirements"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Consumer Configuration"
        verbose_name_plural = "Consumer Configurations"
        ordering = ('app_name',)
    
    def __str__(self):
        status = "✅" if self.is_active else "❌"
        return f"{status} {self.get_app_name_display()} → {self.get_primary_provider_display()}"
    
    def clean(self):
        """Validate the configuration."""
        if self.primary_provider == self.fallback_provider:
            raise ValidationError("Primary and fallback providers cannot be the same")
    
    @property
    def provider_config(self):
        """Get the provider configuration for this consumer."""
        return {
            'consumer': self.app_name,
            'primary_provider': self.primary_provider,
            'fallback_provider': self.fallback_provider,
            'is_active': self.is_active
        }