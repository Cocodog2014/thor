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
from django.http import JsonResponse
from django.views.generic import RedirectView
from GlobalMarkets.views import api_test_page, debug_market_times, sync_markets
# Legacy import (can be removed after testing)
# from SchwabLiveData.views import schwab_auth_callback
# from SchwabLiveData.admin_views import cloudflared_control

def api_root(request):
    """Simple API root that shows available endpoints"""
    return JsonResponse({
        'message': 'Thor API Server',
        'version': '1.0',
        'endpoints': {
            'admin': '/admin/',
            'api': '/api/',
            'schwab': '/api/schwab/',
            'tos': '/api/feed/tos/',
            'worldclock': '/api/worldclock/',
            'futures': '/api/futures/',
        }
    })

urlpatterns = [
    # Root endpoint
    path('', api_root, name='api_root'),
    # Custom admin utility views (TODO: migrate from old SchwabLiveData)
    # path('admin/cloudflared/', cloudflared_control, name='admin_cloudflared_control'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),           # Thor APIs
    path('api/', include('FutureTrading.urls')), # Future Trading APIs
    path('api/users/', include('users.urls')),   # User authentication
    # LiveData endpoints (new structure)
    path('api/schwab/', include(('LiveData.schwab.urls', 'schwab'), namespace='schwab')),
    path('api/feed/', include(('LiveData.shared.urls', 'feed'), namespace='feed')),
    path('api/feed/tos/', include(('LiveData.tos.urls', 'tos'), namespace='tos')),
    path('api/worldclock/', include('GlobalMarkets.urls')),      # Legacy path (kept)
    path('api/global-markets/', include('GlobalMarkets.urls')),  # Preferred path
    path('api/world-markets/', include('GlobalMarkets.urls')),   # Friendly alias
    path('test/', api_test_page, name='api_test'),  # API test page
    path('debug/', debug_market_times, name='debug_market_times'),  # Debug endpoint
    path('sync/', sync_markets, name='sync_markets'),  # Sync markets endpoint
    # TODO: Migrate OAuth callbacks after testing
    # Root-level OAuth callback to match Schwab portal setting (e.g., https://360edu.org/auth/callback)
    # path('auth/callback', schwab_auth_callback, name='schwab_auth_callback_root'),
    # Alternate root-level path if your Schwab portal uses /schwab/callback
    # path('schwab/callback', schwab_auth_callback, name='schwab_auth_callback_alt'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
