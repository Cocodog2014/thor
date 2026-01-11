# ActAndPos/urls.py
from django.urls import include, path
from ActAndPos.views.accounts import accounts_view

app_name = "ActAndPos"

urlpatterns = [
    # Unified accounts endpoint
    path("accounts", accounts_view, name="actandpos-accounts"),

    # Split-domain endpoints
    path("paper/", include("ActAndPos.paper.urls")),
    path("live/", include("ActAndPos.live.urls")),
]

