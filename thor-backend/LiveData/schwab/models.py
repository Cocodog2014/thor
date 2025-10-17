"""
Schwab OAuth token storage.

This is the ONLY model in the Schwab app - just stores OAuth tokens per user.
All other data (positions, balances, orders) comes from the API in real-time
and is published to Redis for consumption by other apps.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SchwabToken(models.Model):
    """
    OAuth tokens for Schwab API access.
    
    Each user can connect one Schwab account. The access/refresh tokens
    are stored here and automatically refreshed when needed.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='schwab_token',
        help_text="Thor user who owns this Schwab connection"
    )
    
    access_token = models.TextField(
        help_text="Short-lived OAuth access token (typically 30 minutes)"
    )
    
    refresh_token = models.TextField(
        help_text="Long-lived refresh token (typically 7 days)"
    )
    
    access_expires_at = models.BigIntegerField(
        help_text="Unix timestamp when access token expires"
    )
    
    # Optional metadata
    schwab_account_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Primary Schwab account ID (if available)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'schwab_token'
        verbose_name = 'Schwab OAuth Token'
        verbose_name_plural = 'Schwab OAuth Tokens'
    
    def __str__(self):
        return f"Schwab Token for {self.user.username}"
    
    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        import time
        return time.time() >= self.access_expires_at
