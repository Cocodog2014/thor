"""
TOS streaming control views.

HTTP endpoints for controlling the TOS streamer (optional).
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from .services import tos_streamer

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def stream_status(request):
    """
    Get current TOS streamer status.
    
    Returns connection status and subscribed symbols.
    """
    return JsonResponse({
        "connected": tos_streamer.is_connected,
        "subscribed_symbols": list(tos_streamer.subscribed_symbols)
    })


@login_required
@require_http_methods(["POST"])
def subscribe_symbol(request):
    """
    Subscribe to quotes for a symbol.
    
    Expects JSON body: {"symbol": "AAPL"}
    """
    symbol = request.POST.get('symbol') or request.GET.get('symbol')
    
    if not symbol:
        return JsonResponse({"error": "Symbol required"}, status=400)
    
    try:
        tos_streamer.subscribe(symbol)
        return JsonResponse({
            "success": True,
            "message": f"Subscribed to {symbol}",
            "symbol": symbol.upper()
        })
    except Exception as e:
        logger.error(f"Failed to subscribe to {symbol}: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unsubscribe_symbol(request):
    """
    Unsubscribe from quotes for a symbol.
    
    Expects JSON body: {"symbol": "AAPL"}
    """
    symbol = request.POST.get('symbol') or request.GET.get('symbol')
    
    if not symbol:
        return JsonResponse({"error": "Symbol required"}, status=400)
    
    try:
        tos_streamer.unsubscribe(symbol)
        return JsonResponse({
            "success": True,
            "message": f"Unsubscribed from {symbol}",
            "symbol": symbol.upper()
        })
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        return JsonResponse({"error": str(e)}, status=500)
