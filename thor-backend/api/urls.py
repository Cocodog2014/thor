from django.urls import path, include
from . import views

urlpatterns = [
    # API Overview
    path('', views.api_overview, name='api-overview'),
    path('stats/', views.api_statistics, name='api-statistics'),
    path('quotes/', views.quotes_snapshot, name='quotes-snapshot'),
    path('quotes/stream/', views.quotes_stream, name='quotes-stream'),
    path('intraday/health/', views.intraday_health, name='intraday-health'),
    # Market session intraday latest
    path('session/', views.session, name='session'),
    # App-level API delegates
    path('global-markets/', include('GlobalMarkets.api_urls')),
]