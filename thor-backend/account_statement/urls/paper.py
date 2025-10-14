"""
Paper account URLs.

Contains URL patterns specific to paper trading accounts.
"""

from django.urls import path
from ..views.paper import (
    PaperAccountListView,
    PaperAccountDetailView, 
    PaperAccountCreateView,
    PaperAccountUpdateView,
    paper_account_reset,
    paper_account_performance,
)

app_name = 'paper'

urlpatterns = [
    # Paper account management
    path('', PaperAccountListView.as_view(), name='list'),
    path('create/', PaperAccountCreateView.as_view(), name='create'),
    path('<int:pk>/', PaperAccountDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', PaperAccountUpdateView.as_view(), name='update'),
    
    # Paper account actions
    path('<int:pk>/reset/', paper_account_reset, name='reset'),
    path('<int:pk>/performance/', paper_account_performance, name='performance'),
]