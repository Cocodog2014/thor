"""
URL Configuration for SchwabLiveData

This module defines the URL patterns for the SchwabLiveData app.
"""

from django.urls import path
from . import views

app_name = 'schwablivedata'

urlpatterns = [
    # Main quotes endpoint (replaces/supplements existing quotes API)
    path('quotes/latest/', views.SchwabQuotesView.as_view(), name='quotes_latest'),
    
    # Provider management endpoints
    path('provider/status/', views.ProviderStatusView.as_view(), name='provider_status'),
    path('provider/health/', views.ProviderHealthView.as_view(), name='provider_health'),

    # OAuth: start and callback endpoints for Schwab
    path('auth/login/', views.schwab_auth_start, name='auth_login'),
    path('auth/callback', views.schwab_auth_callback, name='auth_callback'),
    
    # Legacy endpoint for compatibility
    path('quotes/legacy/', views.schwab_quotes_legacy, name='quotes_legacy'),
]