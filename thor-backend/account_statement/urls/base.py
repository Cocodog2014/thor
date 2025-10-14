"""
Base URLs for account statement functionality.

Contains shared URL patterns and the main routing structure.
"""

from django.urls import path, include
from ..views import account_dashboard

app_name = 'account_statement'

# Base URL patterns
base_patterns = [
    path('', account_dashboard, name='dashboard'),
    path('dashboard/', account_dashboard, name='dashboard_alt'),
]

# Include sub-app URL patterns
urlpatterns = base_patterns + [
    path('paper/', include('account_statement.urls.paper')),
    path('real/', include('account_statement.urls.real')),
]