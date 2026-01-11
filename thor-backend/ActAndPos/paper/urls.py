from django.urls import path

from .views import paper_status_view


urlpatterns = [
    path("status", paper_status_view, name="actandpos-paper-status"),
]
