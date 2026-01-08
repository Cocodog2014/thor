"""GlobalMarkets API URL configuration."""
from django.urls import path
from . import api

urlpatterns = [
    path('markets/', api.markets, name='markets'),
]
