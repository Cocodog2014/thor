import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ActAndPos.models import Account
from ..services import SchwabTraderAPI

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_accounts(request):
    """
    List all Schwab accounts for the authenticated user.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)

        api = SchwabTraderAPI(request.user)
        accounts = api.fetch_accounts() or []
        acct_hash_map = api.get_account_number_hash_map()

        enriched_accounts = []

        for acct in accounts:
            sec = acct.get('securitiesAccount', {}) or {}
            account_number = sec.get('accountNumber') or acct.get('accountNumber')
            account_hash = (
                sec.get('hashValue')
                or acct.get('hashValue')
                or (account_number and acct_hash_map.get(str(account_number)))
                or acct.get('accountId')
            )

            if not account_hash and account_number:
                try:
                    account_hash = api.resolve_account_hash(account_number)
                except Exception:
                    account_hash = None

            if not account_hash:
                logger.warning("Unable to resolve Schwab hashValue for account %s", account_number)
                continue

            display_name = (
                acct.get('displayName')
                or sec.get('displayName')
                or acct.get('nickname')
                or account_number
                or account_hash
            )

            account_obj, _ = Account.objects.get_or_create(
                user=request.user,
                broker='SCHWAB',
                broker_account_id=account_hash,
                defaults={'display_name': display_name, 'currency': 'USD', 'account_number': account_number},
            )

            if account_number and account_obj.account_number != account_number:
                account_obj.account_number = account_number
                account_obj.save(update_fields=["account_number", "updated_at"])

            acct_copy = acct.copy()
            acct_copy['thor_account_id'] = account_obj.id
            acct_copy['broker_account_id'] = account_hash
            acct_copy['account_number'] = account_number
            enriched_accounts.append(acct_copy)

        return JsonResponse({
            "accounts": enriched_accounts
        })

    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab accounts API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error("Failed to fetch accounts: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_summary(request):
    """
    UI-ready summary built from /trader/v1/accounts payload.
    Avoids relying on hashValue, which Schwab may omit.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected",
                "connected": False
            }, status=404)

        api = SchwabTraderAPI(request.user)
        accounts = api.fetch_accounts() or []
        acct_hash_map = api.get_account_number_hash_map()
        logger.info("Schwab account number mapping resolved %s entries", len(acct_hash_map))

        if not accounts:
            return JsonResponse({
                "error": "No Schwab accounts found"
            }, status=404)

        requested_number = request.GET.get('account_number')

        chosen = None
        for acct in accounts:
            sec = (acct or {}).get('securitiesAccount', {}) or {}
            acct_num = sec.get('accountNumber')
            if requested_number and acct_num == requested_number:
                chosen = acct
                break

        if not chosen:
            chosen = accounts[0]

        sec = (chosen or {}).get('securitiesAccount', {}) or {}
        account_number = sec.get('accountNumber') or chosen.get('accountNumber')
        account_hash = acct_hash_map.get(str(account_number)) if account_number else None

        if not account_hash:
            if account_number:
                try:
                    account_hash = api.resolve_account_hash(account_number)
                except Exception:
                    account_hash = None
        if not account_hash:
            return JsonResponse({"error": "Unable to resolve Schwab account hashValue"}, status=502)

        if not account_number:
            return JsonResponse({"error": "Unable to get account identifier"}, status=500)

        balances_payload = api.fetch_balances(account_hash)
        if not balances_payload:
            return JsonResponse({"error": "Unable to fetch balances from Schwab", "success": False}, status=502)

        def _money(v):
            try:
                return f"${float(v):,.2f}"
            except Exception:
                return "$0.00"

        def _pct(v):
            try:
                return f"{float(v):.2f}%"
            except Exception:
                return "0.00%"

        summary = {
            "net_liquidating_value": _money(balances_payload.get("net_liq", 0)),
            "stock_buying_power": _money(balances_payload.get("stock_buying_power", 0)),
            "option_buying_power": _money(balances_payload.get("option_buying_power", 0)),
            "day_trading_buying_power": _money(balances_payload.get("day_trading_buying_power", 0)),
            "available_funds_for_trading": _money(balances_payload.get("available_funds_for_trading", 0)),
            "long_stock_value": _money(balances_payload.get("long_stock_value", 0)),
            "equity_percentage": _pct(balances_payload.get("equity_percentage", 0)),
        }

        return JsonResponse({
            "success": True,
            "account_number": balances_payload.get("account_number") or account_number,
            "account_hash": balances_payload.get("account_hash") or account_hash,
            "balances_published": True,
            "summary": summary
        })

    except Exception as e:
        logger.error("Failed to fetch account summary: %s", e)
        return JsonResponse({
            "error": str(e),
            "success": False
        }, status=500)
