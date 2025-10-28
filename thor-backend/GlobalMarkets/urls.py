from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MarketViewSet,
    USMarketStatusViewSet,
    MarketDataSnapshotViewSet,
    UserMarketWatchlistViewSet,
    worldclock_stats,
    control_markets,
    composite_index,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'markets', MarketViewSet)
router.register(r'us-market-status', USMarketStatusViewSet)
router.register(r'market-snapshots', MarketDataSnapshotViewSet)
router.register(r'user-watchlist', UserMarketWatchlistViewSet, basename='userwatchlist')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Custom function-based views
    path('stats/', worldclock_stats, name='worldclock-stats'),
    path('control-markets/', control_markets, name='control-markets'),
    path('composite/', composite_index, name='composite-index'),
]
