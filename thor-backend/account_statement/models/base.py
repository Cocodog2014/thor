"""
Base account models and shared functionality.

Contains abstract base classes and common models used by both
paper and real trading accounts.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class AccountStatus(models.TextChoices):
    """Account status definitions."""
    ACTIVE = 'ACTIVE', 'Active'
    CLOSED = 'CLOSED', 'Closed'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    PENDING = 'PENDING', 'Pending Approval'


class BaseAccount(models.Model):
    """
    Abstract base class for all trading accounts.
    
    Contains common fields and methods shared between paper and real accounts.
    Based on Schwab account statement fields from the screenshot.
    """
    
    # Core account info
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Account owner"
    )
    
    account_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="External account number (e.g., Schwab account number)"
    )
    
    base_currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Base currency for the account"
    )
    
    status = models.CharField(
        max_length=10,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        help_text="Current account status"
    )
    
    # Account Summary Fields (from Schwab screenshot)
    # All financial fields use DecimalField for precision
    net_liquidating_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total account value if all positions were liquidated"
    )
    
    stock_buying_power = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Available funds for stock purchases"
    )
    
    option_buying_power = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Available funds for option purchases"
    )
    
    available_funds_for_trading = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Available funds for trading activities"
    )
    
    long_stock_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total value of long stock positions"
    )
    
    long_marginable_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Value of long marginable securities"
    )
    
    short_marginable_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Value of short marginable securities"
    )
    
    margin_equity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Equity available for margin trading"
    )
    
    equity_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Equity percentage (0-100)"
    )
    
    maintenance_requirement = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum equity required to maintain positions"
    )
    
    money_market_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Cash balance in money market fund"
    )
    
    # Commission and fees tracking
    equity_commissions_fees_ytd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Year-to-date equity commissions and fees"
    )
    
    option_commissions_fees_ytd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Year-to-date option commissions and fees"
    )
    
    futures_commissions_fees_ytd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Year-to-date futures commissions and fees"
    )
    
    total_commissions_fees_ytd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total year-to-date commissions and fees"
    )
    
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current cash balance"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_statement_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of last account statement update"
    )
    
    class Meta:
        abstract = True
    
    def update_totals(self):
        """Recalculate total fields based on component values."""
        self.total_commissions_fees_ytd = (
            self.equity_commissions_fees_ytd +
            self.option_commissions_fees_ytd +
            self.futures_commissions_fees_ytd
        )
        
        # Update net liquidating value
        self.net_liquidating_value = (
            self.current_balance +
            self.long_stock_value +
            self.long_marginable_value -
            self.short_marginable_value
        )
    
    def get_account_type_display(self):
        """Get human-readable account type."""
        return self.__class__._meta.verbose_name
    
    def save(self, *args, **kwargs):
        """Override save to update calculated fields."""
        self.update_totals()
        super().save(*args, **kwargs)


class AccountSummary(models.Model):
    """
    Historical account summary snapshots.
    
    Stores daily/periodic snapshots of account performance
    for historical tracking and reporting.
    
    This model works with both paper and real accounts via generic foreign key.
    """
    
    # Generic relation to either PaperAccount or RealAccount
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        help_text="Type of account (Paper or Real)"
    )
    object_id = models.PositiveIntegerField(
        help_text="ID of the specific account"
    )
    account = models.GenericForeignKey('content_type', 'object_id')
    
    statement_date = models.DateTimeField(
        help_text="Date and time of this snapshot"
    )
    
    # P&L tracking
    pnl_open = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Unrealized P&L on open positions"
    )
    
    pnl_day = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Daily P&L"
    )
    
    pnl_ytd = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Year-to-date P&L"
    )
    
    pnl_percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="P&L percentage"
    )
    
    # Snapshot of key account values
    margin_requirement = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Margin requirement at snapshot time"
    )
    
    mark_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Mark-to-market value of positions"
    )
    
    net_liquidating_value_snapshot = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Net liquidating value at snapshot time"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Account Summary'
        verbose_name_plural = 'Account Summaries'
        ordering = ['-statement_date']
        unique_together = [['content_type', 'object_id', 'statement_date']]
    
    def __str__(self):
        """String representation of the summary."""
        return f"{self.account} - {self.statement_date.date()}"
    
    def calculate_pnl_percent(self):
        """Calculate P&L percentage based on account starting balance."""
        # This will need to be implemented based on the specific account type
        if hasattr(self.account, 'starting_balance') and self.account.starting_balance > 0:
            self.pnl_percent = (self.pnl_ytd / self.account.starting_balance) * 100
        else:
            self.pnl_percent = Decimal('0.0000')
    
    def save(self, *args, **kwargs):
        """Override save to calculate derived fields."""
        self.calculate_pnl_percent()
        super().save(*args, **kwargs)