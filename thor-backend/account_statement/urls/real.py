"""
Real account URLs.

Contains URL patterns specific to real money trading accounts.
"""

from django.urls import path
from ..views.real import (
    RealAccountListView,
    RealAccountDetailView,
    RealAccountCreateView,
    RealAccountUpdateView,
    real_account_sync,
    real_account_verify,
    real_account_risk_status,
)

app_name = 'real'

urlpatterns = [
    # Real account management
    path('', RealAccountListView.as_view(), name='list'),
    path('create/', RealAccountCreateView.as_view(), name='create'),
    path('<int:pk>/', RealAccountDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', RealAccountUpdateView.as_view(), name='update'),
    
    # Real account actions
    path('<int:pk>/sync/', real_account_sync, name='sync'),
    path('<int:pk>/verify/', real_account_verify, name='verify'),
    path('<int:pk>/risk-status/', real_account_risk_status, name='risk_status'),
]