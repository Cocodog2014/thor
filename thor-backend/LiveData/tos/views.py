"""
TOS streaming control views.

HTTP endpoints for controlling the TOS streamer (optional).
Also provides quotes endpoint for reading TOS RTD data from Excel.

Configuration for TOS Excel RTD reader is in FutureTrading settings,
not here - this is just a generic data provider.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .services import tos_streamer
from .excel_reader import get_tos_excel_reader
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

# TOS Excel configuration - passed from FutureTrading consumer
# This is set by FutureTrading views when they call get_latest_quotes
TOS_EXCEL_CONFIG = None


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
    
    Uses a Redis lock to ensure only one Excel reader runs at a time,
    preventing double-open and COM stalls.
    
    Query params:
        consumer: Consumer app name (for logging)
        file_path: Excel file path (optional, uses default if not provided)
        sheet_name: Sheet name (optional, default: "LiveData")
        data_range: Data range (optional, default passed by consumer)
    """
    consumer = request.GET.get('consumer', 'unknown')
    
    # Allow consumer to specify configuration, default to RTD_TOS.xlsm
    file_path = request.GET.get('file_path', r'A:\Thor\RTD_TOS.xlsm')
    sheet_name = request.GET.get('sheet_name', 'LiveData')
    # Include new 52-week columns (adds one more column: AskSize at N)
    data_range = request.GET.get('data_range', 'A1:N13')  # Default to futures range (1 header + 12 data rows)
    
    # Try to acquire lock (non-blocking)
    if not live_data_redis.acquire_excel_lock(timeout=10):
        logger.warning(f"Excel read already in progress, skipping (consumer: {consumer})")
        return Response({
            'quotes': [],
            'count': 0,
            'source': 'TOS_RTD_Excel',
            'message': 'Excel read in progress by another process',
            'config': {
                'file': file_path,
                'sheet': sheet_name,
                'range': data_range
            }
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        # Get Excel reader instance with consumer-provided config
        reader = get_tos_excel_reader(file_path, sheet_name, data_range)
        
        if not reader:
            logger.warning(f"TOS Excel reader not available (consumer: {consumer})")
            return Response({
                'rows': [],
                'total': {},
                'error': 'TOS Excel reader not configured'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            # Read current data from Excel (include_headers=True since range includes header row)
            quotes = reader.read_data(include_headers=True)

            # Publish to Redis and cache snapshot for each quote
            for q in quotes:
                symbol = q.get('symbol')
                if not symbol:
                    continue
                q['source'] = q.get('source') or 'TOS'
                # Publish as-is; redis client handles Decimal via default=str
                live_data_redis.publish_quote(symbol, q, broadcast_ws=True)
            
            logger.debug(f"Serving {len(quotes)} quotes to {consumer} from {data_range}")
            
            # Return raw quotes - FutureTrading will enrich with signals and compute total
            return Response({
                'quotes': quotes,
                'count': len(quotes),
                'source': 'TOS_RTD_Excel',
                'config': {
                    'file': file_path,
                    'sheet': sheet_name,
                    'range': data_range
                }
            }, status=status.HTTP_200_OK)
        
        finally:
            # CRITICAL: Always disconnect to release Excel COM connection
            # This prevents Excel from freezing when polled frequently
            reader.disconnect()
    
    except Exception as e:
        logger.error(f"Error reading TOS Excel data: {e}")
        return Response({
            'error': 'Failed to read TOS data',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # Always release lock, even if read failed
        live_data_redis.release_excel_lock()
