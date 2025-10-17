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
    # TODO: Build actual Schwab OAuth URL
    # oauth_url = (
    #     f"https://api.schwabapi.com/v1/oauth/authorize"
    #     f"?client_id={settings.SCHWAB_CLIENT_ID}"
    #     f"&redirect_uri={settings.SCHWAB_REDIRECT_URI}"
    #     f"&response_type=code"
    # )
    
    return JsonResponse({
        "error": "Schwab OAuth not yet implemented",
        "message": "This endpoint will redirect to Schwab authorization"
    }, status=501)


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
