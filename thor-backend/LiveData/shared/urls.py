# GlobalMarkets/urls.py
from django.urls import path, include

urlpatterns = [
    # Expose the GlobalMarkets HTTP API endpoints
    path("", include("GlobalMarkets.api_urls")),
]
