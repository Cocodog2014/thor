from django.urls import path

from .views import live_status_view


urlpatterns = [
    path("status", live_status_view, name="actandpos-live-status"),
]
