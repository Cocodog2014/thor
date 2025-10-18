"""
Schwab OAuth and API views.

Handles OAuth flow and API endpoints for Schwab integration.
"""

import logging
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .models import SchwabToken
from .tokens import exchange_code_for_tokens, get_token_expiry
from .services import SchwabTraderAPI

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def oauth_start(request):
    """
    Start Schwab OAuth flow.
    
    Redirects user to Schwab authorization page.
    """
    from django.conf import settings
    from urllib.parse import urlencode
    
    # Build OAuth authorization URL
    client_id = getattr(settings, 'SCHWAB_CLIENT_ID', None)
    redirect_uri = getattr(settings, 'SCHWAB_REDIRECT_URI', None)
    
    if not client_id or not redirect_uri:
        return JsonResponse({
            "error": "Schwab OAuth not configured",
            "message": "Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI in settings"
        }, status=500)
    
    # Schwab OAuth authorization endpoint
    auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'api'  # Adjust scopes as needed
    }
    
    oauth_url = f"{auth_url}?{urlencode(params)}"
    
    logger.info(f"Starting Schwab OAuth for user {request.user.username}")
    logger.info(f"Redirect URI: {redirect_uri}")
    
    # Redirect to Schwab
    return HttpResponseRedirect(oauth_url)


@login_required
@require_http_methods(["GET"])
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
        SchwabToken.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'access_expires_at': get_token_expiry(token_data['expires_in'])
            }
        )
        
        logger.info(f"Successfully connected Schwab account for {request.user.username}")
        
        return JsonResponse({
            "success": True,
            "message": "Schwab account connected successfully"
        })
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab OAuth not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def list_accounts(request):
    """
    List all Schwab accounts for the authenticated user.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        accounts = api.fetch_accounts()
        
        return JsonResponse({
            "accounts": accounts
        })
        
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab accounts API not yet implemented"
        }, status=501)
    except Exception as e:
        logger.error(f"Failed to fetch accounts: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_positions(request, account_id):
    """
    Fetch positions for a specific account.
    
    Publishes positions to Redis for consumption by other apps.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
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


@login_required
@require_http_methods(["GET"])
def get_balances(request, account_id):
    """
    Fetch balances for a specific account.
    
    Publishes balances to Redis for consumption by other apps.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
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


@login_required
@require_http_methods(["GET"])
def account_summary(request):
    """
    Get account summary for display in the frontend.
    
    Returns formatted account balance and buying power information.
    Query params:
        - account_hash: Schwab encrypted account number (optional, uses first account if omitted)
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
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
