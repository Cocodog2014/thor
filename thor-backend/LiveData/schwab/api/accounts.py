# thor-backend/LiveData/schwab/api/accounts.py
import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from LiveData.schwab.utils import get_schwab_connection

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_accounts(request):
    """List all Schwab accounts for the authenticated user."""
    try:
        connection = get_schwab_connection(request.user)
        if not connection:
            return JsonResponse([], safe=False, status=200)

        # Prefer explicit cached broker_account_id; otherwise discover via /accounts/accountNumbers.
        accounts: list[dict] = []
        cached = (getattr(connection, "broker_account_id", None) or "").strip()
        if cached:
            accounts.append({"broker_account_id": cached, "display_name": "Schwab Account"})
            return JsonResponse(accounts, safe=False)

        try:
            from ActAndPos.live.brokers.schwab.sync import _fetch_account_numbers_map

            mapping = _fetch_account_numbers_map(request.user)
            for account_number, account_hash in (mapping or {}).items():
                if not account_hash:
                    continue
                accounts.append(
                    {
                        "broker_account_id": str(account_hash),
                        "display_name": str(account_number or "Schwab Account"),
                    }
                )
        except Exception as exc:
            logger.error("Failed to resolve Schwab accountNumbers: %s", exc)

        return JsonResponse(accounts, safe=False)

    except NotImplementedError:
        return JsonResponse({"error": "Schwab accounts API not yet implemented"}, status=501)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch accounts: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_summary(request):
    """UI-ready summary built from /trader/v1/accounts payload."""
    try:
        connection = get_schwab_connection(request.user)
        if not connection:
            return JsonResponse({"connected": False, "trading_enabled": False})

        trading_enabled = bool(getattr(connection, "trading_enabled", False))
        return JsonResponse({"connected": True, "trading_enabled": trading_enabled})

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch account summary: %s", exc)
        return JsonResponse({"error": str(exc), "success": False}, status=500)
