from django.urls import path

from .views_statement import statement_view


urlpatterns = [
    path("statement", statement_view, name="actandpos-shared-statement"),
]
