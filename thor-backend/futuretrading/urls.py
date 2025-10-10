from django.urls import path
from .views import LatestQuotesView

from . import views

app_name = 'FutureTrading'

urlpatterns = [
    path('quotes/latest', LatestQuotesView.as_view(), name='quotes-latest'),
]