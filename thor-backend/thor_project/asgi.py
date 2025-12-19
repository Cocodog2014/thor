"""
ASGI config for thor_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/

WebSocket Server:
- Runs on ws://localhost:8000/ws/
- Message types: heartbeat, account_balance, positions, intraday_bar, market_status, vwap_update, etc.
- Uses Redis channel layer for group broadcasting
- Non-blocking broadcasts ensure heartbeat never stalls
- Check console for shadow mode logs (all messages logged regardless of feature flag)
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import routing after Django initialization
from thor_project.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        # Django's ASGI application to handle traditional HTTP requests
        "http": django_asgi_app,
        # WebSocket handler with authentication
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        ),
    }
)
