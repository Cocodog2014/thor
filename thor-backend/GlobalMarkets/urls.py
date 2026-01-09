# GlobalMarkets/urls.py
from django.urls import path, include

urlpatterns = [
    path("", include("GlobalMarkets.api_urls")),
]

