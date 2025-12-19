from django.db import models
from .market import Market


class UserMarketWatchlist(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='market_watchlist')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['user', 'market']
        verbose_name = 'User Market Watchlist'
        verbose_name_plural = 'User Market Watchlists'

    def __str__(self):
        display = self.display_name if self.display_name else str(self.market)
        return f"{self.user.username} - {display}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            UserMarketWatchlist.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
