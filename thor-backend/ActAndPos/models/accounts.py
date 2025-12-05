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

    stock_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    option_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    day_trading_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.broker_account_id

    @property
    def ok_to_trade(self) -> bool:
        """Simple guard to flag accounts without capital."""

        return self.net_liq > 0 and self.day_trading_buying_power > 0
