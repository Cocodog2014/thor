"""
Schwab OAuth URL routes.

Handles OAuth flow endpoints:
- /oauth/start - Initiates OAuth flow
- /oauth/callback - Handles OAuth redirect
- /accounts - Lists connected accounts
"""

from django.urls import path
from . import views

app_name = 'schwab'

urlpatterns = [
    # OAuth flow
    path('oauth/start/', views.oauth_start, name='oauth_start'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    
    # Account management
    path('accounts/', views.list_accounts, name='list_accounts'),
    path('accounts/<str:account_id>/positions/', views.get_positions, name='get_positions'),
    path('accounts/<str:account_id>/balances/', views.get_balances, name='get_balances'),
    
    # Account summary for frontend
    path('account/summary/', views.account_summary, name='account_summary'),
]
