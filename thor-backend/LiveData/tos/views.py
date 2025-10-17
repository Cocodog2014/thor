"""
TOS streaming control views.

HTTP endpoints for controlling the TOS streamer (optional).
Also provides quotes endpoint for reading TOS RTD data from Excel.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import tos_streamer
from .excel_reader import get_tos_excel_reader

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


@api_view(['GET'])
def get_latest_quotes(request):
    """
    Get latest quotes from TOS Excel RTD
    
    Returns raw quote data from Excel for FutureTrading app to process.
    FutureTrading will apply signal classification and compute composites.
    
    Query params:
        consumer: Consumer app name (for logging)
    """
    consumer = request.GET.get('consumer', 'unknown')
    
    try:
        # Get Excel reader instance
        reader = get_tos_excel_reader()
        
        if not reader:
            logger.warning(f"TOS Excel reader not available (consumer: {consumer})")
            return Response({
                'rows': [],
                'total': {},
                'error': 'TOS Excel reader not configured'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Read current data from Excel
        quotes = reader.read_data()
        
        logger.debug(f"Serving {len(quotes)} quotes to {consumer}")
        
        # Return raw quotes - FutureTrading will enrich with signals and compute total
        return Response({
            'quotes': quotes,
            'count': len(quotes),
            'source': 'TOS_RTD_Excel'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error reading TOS Excel data: {e}")
        return Response({
            'error': 'Failed to read TOS data',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
