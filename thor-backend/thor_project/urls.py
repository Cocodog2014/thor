"""
URL configuration for thor_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from timezones.views import api_test_page, debug_market_times, sync_markets

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),           # Thor APIs
    path('api/', include('futuretrading.urls')), # Future Trading APIs
    path('api/schwab/', include('SchwabLiveData.urls')), # Schwab Data Provider APIs
    path('api/worldclock/', include('timezones.urls')),  # WorldClock APIs
    path('test/', api_test_page, name='api_test'),  # API test page
    path('debug/', debug_market_times, name='debug_market_times'),  # Debug endpoint
    path('sync/', sync_markets, name='sync_markets'),  # Sync markets endpoint
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
