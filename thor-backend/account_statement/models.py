"""
Account Statement models for Thor trading platform.

This app manages trading accounts and their financial summaries,
supporting both paper trading and real money accounts.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class AccountType(models.TextChoices):
    """Account type definitions."""
    PAPER = 'PAPER', 'Paper Trading Account'
    REAL = 'REAL', 'Real Money Account'


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
    
    # Paper account defaults
    starting_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('100000.00'),
        help_text="Initial balance for paper accounts"
    )
    
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('100000.00'),
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
        verbose_name = 'Trading Account'
        verbose_name_plural = 'Trading Accounts'
        ordering = ['user', 'account_type']
        unique_together = [['user', 'account_type']]  # One paper, one real per user
    
    def __str__(self):
        """String representation of the account."""
        return f"{self.user.email} - {self.get_account_type_display()}"
    
    def is_paper_account(self):
        """Check if this is a paper trading account."""
        return self.account_type == AccountType.PAPER
    
    def is_real_account(self):
        """Check if this is a real money account."""
        return self.account_type == AccountType.REAL
    
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
    
    def save(self, *args, **kwargs):
        """Override save to update calculated fields."""
        self.update_totals()
        
        # Set defaults for paper accounts
        if self.account_type == AccountType.PAPER:
            if not self.account_number:
                self.account_number = f"PAPER-{self.user.id}-{timezone.now().strftime('%Y%m%d')}"
            
            # Initialize paper account balances if new
            if not self.pk:  # New account
                self.current_balance = self.starting_balance
                self.net_liquidating_value = self.starting_balance
                self.stock_buying_power = self.starting_balance
                self.option_buying_power = self.starting_balance
                self.available_funds_for_trading = self.starting_balance
        
        super().save(*args, **kwargs)


class AccountSummary(models.Model):
    """
    Historical account summary snapshots.
    
    Stores daily/periodic snapshots of account performance
    for historical tracking and reporting.
    """
    
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='summaries',
        help_text="Associated trading account"
    )
    
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
        unique_together = [['account', 'statement_date']]  # One summary per account per day
    
    def __str__(self):
        """String representation of the summary."""
        return f"{self.account} - {self.statement_date.date()}"
    
    def calculate_pnl_percent(self):
        """Calculate P&L percentage based on account starting balance."""
        if self.account.starting_balance > 0:
            self.pnl_percent = (self.pnl_ytd / self.account.starting_balance) * 100
        else:
            self.pnl_percent = Decimal('0.0000')
    
    def save(self, *args, **kwargs):
        """Override save to calculate derived fields."""
        self.calculate_pnl_percent()
        super().save(*args, **kwargs)
