from django.db import models


class Position(models.Model):
    """Current position snapshot for an account."""

    ASSET_TYPE_CHOICES = [
        ("EQ", "Equity"),
        ("FUT", "Future"),
        ("OPT", "Option"),
        ("FX", "Forex"),
    ]

    account = models.ForeignKey(
        "ActAndPos.Account",
        on_delete=models.CASCADE,
        related_name="positions",
    )

    symbol = models.CharField(max_length=32)
    description = models.CharField(max_length=128, blank=True)
    asset_type = models.CharField(max_length=8, choices=ASSET_TYPE_CHOICES, default="EQ")

    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    avg_price = models.DecimalField(max_digits=18, decimal_places=6)

    mark_price = models.DecimalField(max_digits=18, decimal_places=6, default=0)

    realized_pl_open = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    realized_pl_day = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    multiplier = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=1,
        help_text="Contract multiplier (e.g. ES=50, CL=1000).",
    )

    currency = models.CharField(max_length=8, default="USD")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("account", "symbol", "asset_type")

    def __str__(self) -> str:
        return f"{self.account} {self.symbol} {self.quantity}"

    @property
    def market_value(self):
        return self.quantity * self.mark_price * self.multiplier

    @property
    def cost_basis(self):
        return self.quantity * self.avg_price * self.multiplier

    @property
    def unrealized_pl(self):
        return self.market_value - self.cost_basis

    @property
    def pl_percent(self):
        if self.cost_basis == 0:
            return 0
        return (self.unrealized_pl / abs(self.cost_basis)) * 100
