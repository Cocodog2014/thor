# ActAndPos/urls.py
from django.urls import include, path

app_name = "ActAndPos"

urlpatterns = [
    # Split-domain endpoints
    path("paper/", include("ActAndPos.paper.urls")),
    path("live/", include("ActAndPos.live.urls")),
]

