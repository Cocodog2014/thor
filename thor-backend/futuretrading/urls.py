from django.urls import path
from .views.RTD import LatestQuotesView

app_name = 'FutureTrading'

urlpatterns = [
    path('quotes/latest', LatestQuotesView.as_view(), name='quotes-latest'),
]