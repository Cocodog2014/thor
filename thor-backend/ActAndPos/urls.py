# ActAndPos/urls.py
from django.urls import include, path

from ActAndPos.accounts_view import accounts_view
from ActAndPos.shared.views import activity_today_view

app_name = "ActAndPos"

urlpatterns = [
    # Unified accounts endpoint
    path("accounts", accounts_view, name="actandpos-accounts"),

    # Unified cross-domain endpoints (paper + live)
    path("activity/today", activity_today_view, name="actandpos-activity-today"),
    path("", include("ActAndPos.shared.urls")),

    # Split-domain endpoints
    path("paper/", include("ActAndPos.paper.urls")),
    path("live/", include("ActAndPos.live.urls")),
]

