"""
TOS streaming URL routes.

Optional HTTP endpoints for controlling the TOS streamer.
Also provides quotes endpoint for TOS RTD Excel data.
"""

from django.urls import path
from . import views

app_name = 'tos'

urlpatterns = [
    path('status/', views.stream_status, name='stream_status'),
    path('subscribe/', views.subscribe_symbol, name='subscribe_symbol'),
    path('unsubscribe/', views.unsubscribe_symbol, name='unsubscribe_symbol'),
    path('quotes/latest/', views.get_latest_quotes, name='latest_quotes'),
]
