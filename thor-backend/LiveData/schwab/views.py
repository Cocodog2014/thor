"""
Schwab OAuth and API views.

Handles OAuth flow and API endpoints for Schwab integration.
"""

import logging
import time
from urllib.parse import urlencode

from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ActAndPos.models import Account

from .models import BrokerConnection
from .tokens import exchange_code_for_tokens, get_token_expiry
from .services import SchwabTraderAPI

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def schwab_health(request):
    """Read-only Schwab health endpoint (no outbound Schwab calls)."""
    connection = getattr(request.user, 'schwab_token', None)

    if not connection:
        return Response({
            "connected": False,
            "broker": BrokerConnection.BROKER_SCHWAB,
            "approval_state": "not_connected",
            "last_error": None,
        })

    now = int(time.time())
    expires_at = int(connection.access_expires_at or 0)
    seconds_until_expiry = max(0, expires_at - now)
    token_expired = now >= expires_at

    approval_state = "trading_enabled" if connection.trading_enabled else "read_only"

    return Response({
        "connected": not token_expired,
        "broker": connection.broker,
        "token_expired": token_expired,
        "expires_at": expires_at,
        "seconds_until_expiry": seconds_until_expiry,
        "trading_enabled": connection.trading_enabled,
        "approval_state": approval_state,
        "last_error": None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def oauth_start(request):
    """
    Start Schwab OAuth flow.

    Redirects user to Schwab authorization page.
    """
    # Raw client_id from settings (no suffix)
    raw_client_id = getattr(settings, 'SCHWAB_CLIENT_ID', None)
    redirect_uri = getattr(settings, 'SCHWAB_REDIRECT_URI', None)

    if not raw_client_id or not redirect_uri:
        return JsonResponse({
            "error": "Schwab OAuth not configured",
            "message": "Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI in settings"
        }, status=500)

    # Schwab wants @AMER.OAUTHAP suffix on the client_id for TOKEN endpoint only,
    # NOT for the authorize endpoint. Use raw client_id for authorize.
    client_id_for_auth = raw_client_id

    auth_url = "https://api.schwabapi.com/v1/oauth/authorize"

    params = {
        'client_id': client_id_for_auth,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'api',  # standard scope from Schwab docs
    }

    oauth_url = f"{auth_url}?{urlencode(params)}"

    logger.info(f"Starting Schwab OAuth for user {request.user.username}")
    logger.info(f"Raw client_id: {raw_client_id}")
    logger.info(f"Client_id for auth: {client_id_for_auth}")
    logger.info(f"Redirect URI: {redirect_uri}")
    logger.info(f"Auth URL: {oauth_url}")

    return JsonResponse({"auth_url": oauth_url})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def oauth_callback(request):
    """
    Handle OAuth callback from Schwab.
    
    Exchanges authorization code for tokens and saves to database.
    """
    auth_code = request.GET.get('code')
    
    if not auth_code:
        return JsonResponse({"error": "No authorization code provided"}, status=400)
    
    try:
        # Exchange code for tokens
        token_data = exchange_code_for_tokens(auth_code)
        
        # Save tokens to database
        BrokerConnection.objects.update_or_create(
            user=request.user,
            broker=BrokerConnection.BROKER_SCHWAB,
            defaults={
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'access_expires_at': get_token_expiry(token_data['expires_in'])
            }
        )
        
        logger.info(f"Successfully connected Schwab account for {request.user.username}")

        # Send user back to the frontend after successful connect
        frontend_url = getattr(settings, "FRONTEND_BASE_URL", "https://dev-thor.360edu.org").rstrip("/")
        params = urlencode({"schwab": "connected"})
        return redirect(f"{frontend_url}/broker-connections?{params}")
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab OAuth not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


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
        accounts = api.fetch_accounts()

        enriched_accounts = []

        for acct in accounts:
            account_hash = acct.get('hashValue') or acct.get('accountNumber') or acct.get('accountId')
            if not account_hash:
                continue

            display_name = acct.get('displayName') or acct.get('nickname') or account_hash

            account_obj, _ = Account.objects.get_or_create(
                user=request.user,
                broker='SCHWAB',
                broker_account_id=account_hash,
                defaults={'display_name': display_name, 'currency': 'USD'},
            )

            acct_copy = acct.copy()
            acct_copy['thor_account_id'] = account_obj.id
            acct_copy['broker_account_id'] = account_hash
            enriched_accounts.append(acct_copy)

        return JsonResponse({
            "accounts": enriched_accounts
        })
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab accounts API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"Failed to fetch accounts: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_positions(request, account_id):
    """
    Fetch positions for a specific account.
    
    Publishes positions to Redis for consumption by other apps.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        api.fetch_positions(account_id)
        
        return JsonResponse({
            "success": True,
            "message": f"Positions published to Redis for account {account_id}"
        })
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab positions API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balances(request, account_id):
    """
    Fetch balances for a specific account.
    
    Publishes balances to Redis for consumption by other apps.
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        api.fetch_balances(account_id)
        
        return JsonResponse({
            "success": True,
            "message": f"Balances published to Redis for account {account_id}"
        })
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab balances API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"Failed to fetch balances: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_summary(request):
    """
    Get account summary for display in the frontend.
    
    Returns formatted account balance and buying power information.
    Query params:
        - account_hash: Schwab encrypted account number (optional, uses first account if omitted)
    """
    try:
        if not request.user.schwab_token:
            return JsonResponse({
                "error": "No Schwab account connected",
                "connected": False
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        
        # Get account_hash from query params, or fetch first account
        account_hash = request.GET.get('account_hash')
        
        if not account_hash:
            # Fetch all accounts and use the first one
            accounts = api.fetch_accounts()
            if not accounts:
                return JsonResponse({
                    "error": "No Schwab accounts found"
                }, status=404)
            
            # Get the first account's hashValue
            first_account = accounts[0]
            account_hash = first_account.get('hashValue')
            
            if not account_hash:
                return JsonResponse({
                    "error": "Unable to get account identifier"
                }, status=500)
        
        # Fetch account summary
        summary = api.get_account_summary(account_hash)
        
        return JsonResponse({
            "success": True,
            "account_hash": account_hash,
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch account summary: {e}")
        return JsonResponse({
            "error": str(e),
            "success": False
        }, status=500)
