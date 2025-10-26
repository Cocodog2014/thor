from django.urls import path
from .views.RTD import LatestQuotesView
from .views.MarketOpen import (
    MarketOpenSessionListView,
    MarketOpenSessionDetailView,
    TodayMarketOpensView,
    PendingMarketOpensView,
    MarketOpenStatsView,
    FutureSnapshotListView,
)

app_name = 'FutureTrading'

urlpatterns = [
    # RTD Futures Quotes
    path('quotes/latest', LatestQuotesView.as_view(), name='quotes-latest'),
    
    # Market Open Sessions
    path('market-opens/', MarketOpenSessionListView.as_view(), name='market-opens-list'),
    path('market-opens/<int:pk>/', MarketOpenSessionDetailView.as_view(), name='market-opens-detail'),
    path('market-opens/today/', TodayMarketOpensView.as_view(), name='market-opens-today'),
    path('market-opens/pending/', PendingMarketOpensView.as_view(), name='market-opens-pending'),
    path('market-opens/stats/', MarketOpenStatsView.as_view(), name='market-opens-stats'),
    
    # Future Snapshots
    path('snapshots/', FutureSnapshotListView.as_view(), name='snapshots-list'),
]