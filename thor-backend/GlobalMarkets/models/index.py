from django.db import models


class GlobalMarketIndex(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    global_composite_score = models.DecimalField(max_digits=6, decimal_places=3)
    asia_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    europe_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    americas_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    markets_open = models.IntegerField(default=0)
    markets_bullish = models.IntegerField(default=0)
    markets_bearish = models.IntegerField(default=0)
    markets_neutral = models.IntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"GlobalIndex @ {self.timestamp:%Y-%m-%d %H:%M} = {self.global_composite_score}"