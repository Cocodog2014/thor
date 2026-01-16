from __future__ import annotations

import asyncio
import logging
from typing import Callable

from django.conf import settings
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class ApprovalRequiredMiddleware:
    """Block authenticated API access until the user is approved.

    This is enforced at middleware level so it applies uniformly even for views that
    specify their own DRF permission_classes.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self._get_response_is_async = asyncio.iscoroutinefunction(get_response)

    def __call__(self, request):
        if self._get_response_is_async:
            return self.__acall__(request)

        try:
            return self._handle_request(request)
        except asyncio.CancelledError:
            # Most commonly: browser navigated/refresh, request was superseded, or client aborted.
            try:
                logger.warning(
                    "Request cancelled: %s %s",
                    getattr(request, "method", "?"),
                    request.get_full_path() if hasattr(request, "get_full_path") else getattr(request, "path", "?"),
                )
            finally:
                raise

    async def __acall__(self, request):
        try:
            return await self._handle_request_async(request)
        except asyncio.CancelledError:
            try:
                logger.warning(
                    "Request cancelled: %s %s",
                    getattr(request, "method", "?"),
                    request.get_full_path() if hasattr(request, "get_full_path") else getattr(request, "path", "?"),
                )
            finally:
                raise

    def _handle_request(self, request):
        require_approval = bool(getattr(settings, "THOR_REQUIRE_ADMIN_APPROVAL", True))
        if not require_approval:
            return self.get_response(request)

        path = request.path or ""

        # Only gate API routes.
        if not path.startswith("/api/"):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        # Admin/staff always allowed.
        if bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            return self.get_response(request)

        is_approved = bool(getattr(user, "is_approved", True))
        if is_approved:
            return self.get_response(request)

        # Allowlist endpoints needed to let users log in and see pending state.
        allow_prefixes = (
            "/api/users/login/",
            "/api/users/register/",
            "/api/users/token/refresh/",
            "/api/users/profile/",
        )
        if any(path.startswith(prefix) for prefix in allow_prefixes):
            return self.get_response(request)

        return JsonResponse(
            {
                "detail": "Your account is pending admin approval.",
                "code": "not_approved",
            },
            status=403,
        )

    async def _handle_request_async(self, request):
        require_approval = bool(getattr(settings, "THOR_REQUIRE_ADMIN_APPROVAL", True))
        if not require_approval:
            return await self.get_response(request)

        path = request.path or ""

        # Only gate API routes.
        if not path.startswith("/api/"):
            return await self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return await self.get_response(request)

        # Admin/staff always allowed.
        if bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            return await self.get_response(request)

        is_approved = bool(getattr(user, "is_approved", True))
        if is_approved:
            return await self.get_response(request)

        # Allowlist endpoints needed to let users log in and see pending state.
        allow_prefixes = (
            "/api/users/login/",
            "/api/users/register/",
            "/api/users/token/refresh/",
            "/api/users/profile/",
        )
        if any(path.startswith(prefix) for prefix in allow_prefixes):
            return await self.get_response(request)

        return JsonResponse(
            {
                "detail": "Your account is pending admin approval.",
                "code": "not_approved",
            },
            status=403,
        )
