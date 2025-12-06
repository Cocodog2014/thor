from decimal import Decimal
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
        q = self.quantity if self.quantity is not None else Decimal("0")
        m = self.mark_price if self.mark_price is not None else Decimal("0")
        mult = self.multiplier if self.multiplier is not None else Decimal("1")
        return q * m * mult

    @property
    def cost_basis(self):
        q = self.quantity if self.quantity is not None else Decimal("0")
        p = self.avg_price if self.avg_price is not None else Decimal("0")
        mult = self.multiplier if self.multiplier is not None else Decimal("1")
        return q * p * mult

    @property
    def unrealized_pl(self):
        return self.market_value - self.cost_basis

    @property
    def pl_percent(self):
        cost = self.cost_basis
        if not cost:  # handles 0 or None
            return 0
        return (self.unrealized_pl / abs(cost)) * 100
