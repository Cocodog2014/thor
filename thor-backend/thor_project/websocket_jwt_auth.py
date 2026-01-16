"""JWT authentication for Django Channels WebSockets.

The frontend primarily authenticates API calls with SimpleJWT (Authorization: Bearer ...).
Browsers cannot set arbitrary headers on a WebSocket handshake, so we support passing
the access token as a query param: `ws(s)://host/ws/?token=<access>`.

This middleware:
- Preserves any existing authenticated user (e.g., session/cookie auth)
- Otherwise attempts to authenticate via SimpleJWT access token
"""

from __future__ import annotations

from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware


def _anonymous_user():
    # Lazy import: Django may not be initialized when this module is imported by Daphne.
    from django.contrib.auth.models import AnonymousUser

    return AnonymousUser()


@sync_to_async
def _get_user(user_id: int):
    try:
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        return UserModel.objects.get(id=int(user_id))
    except Exception:
        return _anonymous_user()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope = dict(scope)

        user = scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            try:
                raw_qs = scope.get("query_string", b"")
                query = parse_qs(raw_qs.decode("utf-8"))
                token = (query.get("token") or [None])[0]
            except Exception:
                token = None

            if token:
                try:
                    # Lazy import: pulls in DRF/SimpleJWT settings.
                    from rest_framework_simplejwt.tokens import AccessToken

                    validated = AccessToken(token)
                    user_id = validated.get("user_id")
                    if user_id is not None:
                        scope["user"] = await _get_user(int(user_id))
                    else:
                        scope["user"] = _anonymous_user()
                except Exception:
                    scope["user"] = _anonymous_user()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """Helper to mirror Channels' AuthMiddlewareStack pattern."""

    return JwtAuthMiddleware(inner)
