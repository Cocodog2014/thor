"""
Real money trading account model.

Contains the RealAccount model with real-money-specific functionality
and integration with actual brokerage accounts.
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal
from .base import BaseAccount


class BrokerageProvider(models.TextChoices):
    """Supported brokerage providers."""
    SCHWAB = 'SCHWAB', 'Charles Schwab'
    INTERACTIVE_BROKERS = 'IB', 'Interactive Brokers'  # Using 'IB' as database value
    TD_AMERITRADE = 'TDA', 'TD Ameritrade'
    FIDELITY = 'FIDELITY', 'Fidelity'
    OTHER = 'OTHER', 'Other Brokerage'


class RealAccount(BaseAccount):
    """
    Real money trading account model.
    
    Represents an actual brokerage account with real money.
    Each user can have multiple real accounts from different brokers.
    """
    
    # Real account specific fields
    brokerage_provider = models.CharField(
        max_length=30,  # Increased to accommodate longer provider names
        choices=BrokerageProvider.choices,
        default=BrokerageProvider.SCHWAB,
        help_text="Brokerage provider for this account"
    )
    
    external_account_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="External account ID from brokerage API"
    )
    
    account_nickname = models.CharField(
        max_length=100,
        blank=True,
        help_text="User-defined nickname for this account"
    )
    
    # Account verification and compliance
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether account has been verified with brokerage"
    )
    
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date account was verified"
    )
    
    # Trading permissions
    day_trading_enabled = models.BooleanField(
        default=False,
        help_text="Whether day trading is enabled"
    )
    
    margin_enabled = models.BooleanField(
        default=False,
        help_text="Whether margin trading is enabled"
    )
    
    options_level = models.PositiveSmallIntegerField(
        default=0,
        help_text="Options trading level (0-4)"
    )
    
    # API integration
    api_enabled = models.BooleanField(
        default=False,
        help_text="Whether API access is configured"
    )
    
    last_sync_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful sync with brokerage API"
    )
    
    sync_errors = models.PositiveIntegerField(
        default=0,
        help_text="Number of consecutive sync errors"
    )
    
    # Risk management
    daily_loss_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum daily loss limit"
    )
    
    position_size_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum position size limit"
    )
    
    # Enable easy access to summaries
    summaries = GenericRelation('AccountSummary')
    
    class Meta:
        verbose_name = 'Real Money Account'
        verbose_name_plural = 'Real Money Accounts'
        ordering = ['user__email', 'brokerage_provider']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'external_account_id'],
                name='unique_external_account_per_user',
                condition=models.Q(external_account_id__isnull=False)
            )
        ]
    
    def __str__(self):
        """String representation of the real account."""
        if self.account_nickname:
            return f"{self.user.email} - {self.account_nickname}"
        else:
            return f"{self.user.email} - {self.get_brokerage_provider_display()}"
    
    def is_paper_account(self):
        """Always returns False for real accounts."""
        return False
    
    def is_real_account(self):
        """Always returns True for real accounts."""
        return True
    
    def can_day_trade(self):
        """Check if account can perform day trading."""
        return (
            self.day_trading_enabled and
            self.is_verified and
            self.net_liquidating_value >= Decimal('25000.00')  # PDT rule
        )
    
    def can_trade_options(self):
        """Check if account can trade options."""
        return self.options_level > 0 and self.is_verified
    
    def can_use_margin(self):
        """Check if account can use margin."""
        return self.margin_enabled and self.is_verified
    
    def get_risk_status(self):
        """Get current risk management status."""
        risk_status = {
            'daily_loss_exceeded': False,
            'position_limit_exceeded': False,
            'warnings': []
        }
        
        if self.daily_loss_limit:
            # This would require calculating current day's P&L
            # Implementation depends on how you track daily P&L
            pass
        
        if self.position_size_limit:
            # Check if any position exceeds the limit
            # Implementation depends on position tracking
            pass
        
        return risk_status
    
    def sync_with_brokerage(self):
        """
        Sync account data with brokerage API.
        
        This is a placeholder for actual API integration.
        """
        try:
            # Placeholder for actual brokerage API call
            # This would update account balances, positions, etc.
            
            self.last_sync_date = timezone.now()
            self.sync_errors = 0
            self.save()
            
            return True
        except Exception as e:
            self.sync_errors += 1
            self.save()
            raise e
    
    def save(self, *args, **kwargs):
        """Override save with real account specific logic."""
        # Generate account number if not set
        if not self.account_number:
            if self.external_account_id:
                self.account_number = f"{self.brokerage_provider}-{self.external_account_id}"
            else:
                self.account_number = f"{self.brokerage_provider}-{self.user.id}-{timezone.now().strftime('%Y%m%d%H%M')}"
        
        # Call parent save
        super().save(*args, **kwargs)