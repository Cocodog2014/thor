"""
Real-Time Data (RTD) views

Moved from FutureTrading/views.py for clearer organization. The class
name stays the same so urls don't change.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import threading
import logging
import requests

from ..models import TradingInstrument
from ..models.extremes import Rolling52WeekStats  # still used for extra metadata
from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.constants import SYMBOL_NORMALIZE_MAP

logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    
    Uses LiveData/tos endpoint to get TOS RTD Excel data.
    """

    def get(self, request):
        try:
            rows, total = get_enriched_quotes_with_composite()
            return Response({'rows': rows, 'total': total}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in LatestQuotesView: {str(e)}")
            return Response({'error': 'Internal server error', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RibbonQuotesView(APIView):
    """
    API view that returns live data only for instruments marked with show_in_ribbon=True.
    Returns minimal data optimized for ticker ribbon display.
    """

    def get(self, request):
        try:
            # Get full enriched data
            rows, total = get_enriched_quotes_with_composite()
            
            # Get symbols marked for ribbon display
            ribbon_instruments = TradingInstrument.objects.filter(
                is_active=True,
                show_in_ribbon=True
            ).order_by('sort_order', 'symbol')
            
            # Create a set with both slash and non-slash versions for matching
            ribbon_symbols = set()
            for instr in ribbon_instruments:
                ribbon_symbols.add(instr.symbol)
                # Also add version without leading slash if present
                if instr.symbol.startswith('/'):
                    ribbon_symbols.add(instr.symbol[1:])
                else:
                    ribbon_symbols.add(f'/{instr.symbol}')
            
            logger.info(f"Ribbon symbols configured: {ribbon_symbols}")
            logger.info(f"Available rows: {len(rows)}")
            if rows:
                logger.info(f"First row symbol: {rows[0].get('instrument', {}).get('symbol', 'N/A')}")
            
            # Filter rows to only include ribbon instruments
            ribbon_data = []
            for row in rows:
                symbol = row.get('instrument', {}).get('symbol', '')
                if symbol in ribbon_symbols:
                    ribbon_data.append({
                        'symbol': symbol,
                        'name': row.get('instrument', {}).get('name', ''),
                        'price': row.get('price'),
                        'last': row.get('last'),
                        'change': row.get('change'),
                        'change_percent': row.get('change_percent'),
                        'signal': row.get('signal'),
                    })
            logger.info(f"Returning {len(ribbon_data)} symbols for ribbon")
            
            return Response({
                'symbols': ribbon_data,
                'count': len(ribbon_data),
                'last_updated': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in RibbonQuotesView: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
