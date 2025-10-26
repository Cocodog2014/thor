from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'markets', views.MarketViewSet)
router.register(r'us-market-status', views.USMarketStatusViewSet)
router.register(r'market-snapshots', views.MarketDataSnapshotViewSet)
router.register(r'user-watchlist', views.UserMarketWatchlistViewSet, basename='userwatchlist')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Custom function-based views
    path('stats/', views.worldclock_stats, name='worldclock-stats'),
]
