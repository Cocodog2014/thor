"""
Test views for Schwab OAuth without login requirement.
Use these for initial testing, then switch to real views.
"""

from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.conf import settings
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def oauth_start_test(request):
    """
    Start Schwab OAuth flow - TEST VERSION (no login required).
    
    Redirects to Schwab authorization page.
    """
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
        'scope': 'api'
    }
    
    oauth_url = f"{auth_url}?{urlencode(params)}"
    
    logger.info(f"Starting Schwab OAuth (test mode)")
    logger.info(f"Redirect URI: {redirect_uri}")
    
    # Redirect to Schwab
    return HttpResponseRedirect(oauth_url)


@require_http_methods(["GET"])
def oauth_callback_test(request):
    """
    Handle OAuth callback - TEST VERSION (no login required).
    
    For production, you'll need to associate token with a user.
    """
    auth_code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        return JsonResponse({
            "error": error,
            "message": "OAuth authorization failed"
        }, status=400)
    
    if not auth_code:
        return JsonResponse({
            "error": "No authorization code provided"
        }, status=400)
    
    return JsonResponse({
        "success": True,
        "message": "OAuth code received",
        "code": auth_code[:10] + "...",
        "next_step": "Exchange this code for tokens (not implemented in test view)"
    })
