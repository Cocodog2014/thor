from django.urls import path

from .views import activity_today_view, positions_view

app_name = "ActAndPos"

urlpatterns = [
    path("positions", positions_view, name="positions"),
    path("activity/today", activity_today_view, name="activity-today"),
]
