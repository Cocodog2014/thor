"""URL routes for shared LiveData HTTP endpoints.

Mounted at `/api/feed/` by `thor_project.urls`.
"""

from django.urls import path

from . import views


app_name = "feed"


urlpatterns = [
    path("quotes/snapshot/", views.get_quotes_snapshot, name="quotes_snapshot"),
]
