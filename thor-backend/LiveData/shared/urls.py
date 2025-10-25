from django.urls import path
from .views import get_quotes_snapshot

app_name = 'feed'

urlpatterns = [
    path('quotes/snapshot/', get_quotes_snapshot, name='quotes_snapshot'),
]
