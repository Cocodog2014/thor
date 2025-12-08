from decimal import Decimal

from django.db import models


class Account(models.Model):
    """Trading account summary used by Activities & Positions."""

    BROKER_CHOICES = [
        ("SCHWAB", "Charles Schwab"),
        ("PAPER", "Paper Trading"),
    ]

    broker = models.CharField(max_length=20, choices=BROKER_CHOICES, default="PAPER")
    broker_account_id = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128, blank=True)

    currency = models.CharField(max_length=8, default="USD")

    net_liq = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    starting_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    current_cash = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    stock_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    option_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    day_trading_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    PAPER_DEFAULT_BALANCE = Decimal("100000.00")

    def __str__(self) -> str:
        return self.display_name or self.broker_account_id

    @property
    def ok_to_trade(self) -> bool:
        """Simple guard to flag accounts without capital."""

        return self.net_liq > 0 and self.day_trading_buying_power > 0

    def save(self, *args, **kwargs):
        """Ensure paper accounts start with funded balances."""

        if self._state.adding and self.broker == "PAPER":
            self._initialize_paper_balances()
        super().save(*args, **kwargs)

    def _initialize_paper_balances(self) -> None:
        """Seed default balances for new paper trading accounts."""

        default = self.PAPER_DEFAULT_BALANCE

        if not self.starting_balance:
            self.starting_balance = default

        if not self.cash:
            self.cash = default

        if not self.net_liq:
            self.net_liq = default

        if not self.current_cash:
            self.current_cash = self.cash or default

        if not self.equity:
            self.equity = self.net_liq or default
