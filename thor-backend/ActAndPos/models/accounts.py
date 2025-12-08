from decimal import Decimal

from django.db import models


class Account(models.Model):
    """Trading account summary used by Activities & Positions."""

    BROKER_CHOICES = [
        ("SCHWAB", "Charles Schwab"),
        ("PAPER", "Paper Trading"),
    ]

    COMMISSION_SCHEME_CHOICES = [
        ("NONE", "No per-order commission"),
        ("FLAT_PER_ORDER", "Flat fee per order"),
        ("PCT_NOTIONAL", "Percent of notional value"),
    ]

    BILLING_PLAN_CHOICES = [
        ("NONE", "No monthly billing"),
        ("MONTHLY_FLAT", "Flat monthly fee"),
        ("MONTHLY_PERF", "Monthly performance share"),
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

    commission_scheme = models.CharField(
        max_length=24,
        choices=COMMISSION_SCHEME_CHOICES,
        default="NONE",
        help_text="Controls the per-order commission Thor charges before executing trades.",
    )
    commission_flat_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Flat commission charged every time an order fills (USD).",
    )
    commission_percent_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Percent of notional charged as commission (e.g. 0.005 = 0.5%).",
    )
    trade_fee_flat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Additional flat fee applied per fill (reg/clearing/etc).",
    )

    billing_plan = models.CharField(
        max_length=24,
        choices=BILLING_PLAN_CHOICES,
        default="NONE",
        help_text="How Thor bills this account each month.",
    )
    billing_flat_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Flat subscription charged monthly when billing_plan=Flat.",
    )
    billing_performance_pct = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Percent of monthly profits charged when billing_plan=Performance.",
    )

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
