"""
Schwab OAuth URL routes.

Handles OAuth flow endpoints:
- /oauth/start - Initiates OAuth flow
- /oauth/callback - Handles OAuth redirect
- /accounts - Lists connected accounts
"""

from django.urls import path
from .views import (
    schwab_health,
    oauth_start,
    oauth_callback,
    list_accounts,
    account_summary,
    account_positions,
    get_positions,
    get_balances,
)
from .refresh import refresh_access_token

app_name = 'schwab'

urlpatterns = [
    path('health/', schwab_health, name='health'),
    path('oauth/start/', oauth_start, name='oauth_start'),
    path('oauth/callback/', oauth_callback, name='oauth_callback'),
    path('accounts/', list_accounts, name='list_accounts'),
    path('accounts/<str:account_id>/positions/', get_positions, name='get_positions'),
    path('accounts/<str:account_id>/balances/', get_balances, name='get_balances'),
    path('account/positions/', account_positions, name='account_positions'),
    path('account/summary/', account_summary, name='account_summary'),
    path('refresh/', refresh_access_token, name='refresh_access_token'),
]
