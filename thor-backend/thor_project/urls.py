#THOR/thor-backend/thor_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from LiveData.schwab import views as schwab_views
from ActAndPos.views.balances import account_balance_view

admin.site.site_header = "Thor's Command Center"
admin.site.site_title = "Thor Command Center"
admin.site.index_title = "Thor Command Center"


def api_root(request):
    return JsonResponse({
        'message': 'Thor API Server',
        'version': '1.0',
        'endpoints': {
            'admin': '/admin/',
            'api': '/api/',
            'schwab': '/api/schwab/',
            'tos': '/api/feed/tos/',
            'global_markets': '/api/global-markets/',
        }
    })


urlpatterns = [
    # Root
    path('', api_root, name='api_root'),

    # Admin
    path('admin/', admin.site.urls),

    # ===== CORE MARKET INFRASTRUCTURE =====
    path('api/global-markets/', include('GlobalMarkets.urls')),

    # ===== CORE API APPS =====
    path('api/', include('api.urls')),  # Generic Thor APIs
    path('api/users/', include('users.urls')),
    path('api/instruments/', include('Instruments.urls')),
    path('api/accounts/balance/', account_balance_view, name='account-balance'),

    # ===== LIVE DATA / FEEDS =====
    path('api/schwab/', include(('LiveData.schwab.urls', 'schwab'), namespace='schwab')),
    path('api/feed/', include(('LiveData.shared.urls', 'feed'), namespace='feed')),
    path('api/feed/tos/', include(('LiveData.tos.urls', 'tos'), namespace='tos')),

    # ===== TRADING / POSITIONS =====
    path('api/actandpos/', include(('ActAndPos.urls', 'ActAndPos'), namespace='ActAndPos')),
    path('api/trades/', include(('Trades.urls', 'Trades'), namespace='Trades')),

    # ===== OAUTH CALLBACKS =====
    path('schwab/callback', schwab_views.oauth_callback, name='schwab_callback_public_root'),
    path('schwab/callback/', schwab_views.oauth_callback, name='schwab_callback_public'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

