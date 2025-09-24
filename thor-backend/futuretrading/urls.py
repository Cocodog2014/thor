from django.urls import path
from .views import LatestQuotesView

app_name = 'futuretrading'

urlpatterns = [
    path('quotes/latest', LatestQuotesView.as_view(), name='quotes-latest'),
]