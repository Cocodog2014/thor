from django.urls import path
from . import views

urlpatterns = [
    # API Overview
    path('', views.api_overview, name='api-overview'),
    path('stats/', views.api_statistics, name='api-statistics'),
    path('quotes', views.quotes_snapshot, name='quotes-snapshot'),
    path('quotes/stream', views.quotes_stream, name='quotes-stream'),
    path('vwap/today', views.vwap_today, name='vwap-today'),
    path('vwap/rolling', views.vwap_rolling, name='vwap-rolling'),
    # Market session intraday latest
    path('session', views.session, name='session'),
    # Account Statement summary (paper/real)
    path('account-statement/summary', views.account_statement_summary, name='account-statement-summary'),
    # Paper account reset (dev open; will secure later)
    path('account-statement/reset-paper', views.account_statement_reset_paper, name='account-statement-reset-paper'),
]