from django.urls import path
from . import views

urlpatterns = [
    # API Overview
    path('', views.api_overview, name='api-overview'),
    path('stats/', views.api_statistics, name='api-statistics'),
]