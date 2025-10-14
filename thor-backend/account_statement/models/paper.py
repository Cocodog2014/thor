"""
Paper trading account model.

Contains the PaperAccount model with paper-specific functionality
and defaults for virtual trading.
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone
from decimal import Decimal
from .base import BaseAccount


class PaperAccount(BaseAccount):
    """
    Paper trading account model.
    
    Virtual trading account for practice and testing strategies
    without using real money. Each user gets one paper account.
    """
    
    # Paper-specific fields
    starting_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('10000.00'),
        help_text="Initial virtual balance for paper trading"
    )
    
    reset_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times account has been reset"
    )
    
    last_reset_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of last account reset"
    )
    
    # Enable easy access to summaries
    summaries = GenericRelation('AccountSummary')
    
    class Meta:
        verbose_name = 'Paper Trading Account'
        verbose_name_plural = 'Paper Trading Accounts'
        ordering = ['user__email']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='one_paper_account_per_user'
            )
        ]
    
    def __str__(self):
        """String representation of the paper account."""
        return f"{self.user.email} - Paper Account"
    
    def is_paper_account(self):
        """Always returns True for paper accounts."""
        return True
    
    def is_real_account(self):
        """Always returns False for paper accounts."""
        return False
    
    def reset_account(self):
        """
        Reset paper account to starting balance.
        
        Clears all positions and resets balance to starting amount.
        This is useful for paper trading practice.
        """
        self.current_balance = self.starting_balance
        self.net_liquidating_value = self.starting_balance
        self.stock_buying_power = self.starting_balance
        self.option_buying_power = self.starting_balance
        self.available_funds_for_trading = self.starting_balance
        
        # Clear position values
        self.long_stock_value = Decimal('0.00')
        self.long_marginable_value = Decimal('0.00')
        self.short_marginable_value = Decimal('0.00')
        self.margin_equity = Decimal('0.00')
        self.maintenance_requirement = Decimal('0.00')
        self.money_market_balance = Decimal('0.00')
        
        # Reset fees
        self.equity_commissions_fees_ytd = Decimal('0.00')
        self.option_commissions_fees_ytd = Decimal('0.00')
        self.futures_commissions_fees_ytd = Decimal('0.00')
        self.total_commissions_fees_ytd = Decimal('0.00')
        
        # Update reset tracking
        self.reset_count += 1
        self.last_reset_date = timezone.now()
        
        self.save()
    
    def get_performance_summary(self):
        """Get current performance vs starting balance."""
        if self.starting_balance > 0:
            total_return = self.net_liquidating_value - self.starting_balance
            total_return_percent = (total_return / self.starting_balance) * 100
        else:
            total_return = Decimal('0.00')
            total_return_percent = Decimal('0.00')
        
        return {
            'starting_balance': self.starting_balance,
            'current_value': self.net_liquidating_value,
            'total_return': total_return,
            'total_return_percent': total_return_percent,
            'reset_count': self.reset_count,
        }
    
    def save(self, *args, **kwargs):
        """Override save with paper account specific logic."""
        # Generate paper account number if not set
        if not self.account_number:
            self.account_number = f"PAPER-{self.user.id}-{timezone.now().strftime('%Y%m%d')}"
        
        # Initialize balances for new accounts
        if not self.pk:  # New account
            self.current_balance = self.starting_balance
            self.net_liquidating_value = self.starting_balance
            self.stock_buying_power = self.starting_balance
            self.option_buying_power = self.starting_balance
            self.available_funds_for_trading = self.starting_balance
            self.equity_percentage = Decimal('100.00')
        
        # Call parent save
        super().save(*args, **kwargs)