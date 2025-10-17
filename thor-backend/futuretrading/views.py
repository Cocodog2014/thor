from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Subquery, OuterRef
from django.utils import timezone
from decimal import Decimal
import logging
import requests

from .models import TradingInstrument, MarketData, TradingSignal, SignalStatValue, ContractWeight
from .services.classification import enrich_quote_row, compute_composite

logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    
    Now uses LiveData/tos endpoint to get TOS RTD Excel data.
    """
    
    def get(self, request):
        try:
            # Step 1: Get raw quotes from TOS Excel RTD via LiveData endpoint
            raw_quotes = []
            
            try:
                # Call internal TOS endpoint
                response = requests.get(
                    'http://localhost:8000/api/feed/tos/quotes/latest/',
                    params={'consumer': 'futures_trading'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    raw_quotes = data.get('quotes', [])
                    logger.info(f"Fetched {len(raw_quotes)} quotes from TOS Excel RTD")
                else:
                    logger.warning(f"TOS endpoint returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch TOS data: {e}")
            
            # Step 2: Transform TOS quotes into FutureTrading structure (instrument + fields)
            transformed_rows = []
            for quote in raw_quotes:
                symbol = quote.get('symbol', '')
                
                # Wrap quote data in expected structure
                row = {
                    'instrument': {
                        'symbol': symbol,
                        'name': symbol,
                        'exchange': 'TOS',
                        'currency': 'USD',
                    },
                    'last': float(quote.get('last', 0)) if quote.get('last') else None,
                    'bid': float(quote.get('bid', 0)) if quote.get('bid') else None,
                    'ask': float(quote.get('ask', 0)) if quote.get('ask') else None,
                    'volume': quote.get('volume'),
                    'open': float(quote.get('open', 0)) if quote.get('open') else None,
                    'high': float(quote.get('high', 0)) if quote.get('high') else None,
                    'low': float(quote.get('low', 0)) if quote.get('low') else None,
                    'close': float(quote.get('close', 0)) if quote.get('close') else None,
                    'change': float(quote.get('change', 0)) if quote.get('change') else None,
                    'bid_size': quote.get('bid_size'),
                    'ask_size': quote.get('ask_size'),
                    'timestamp': quote.get('timestamp'),
                    'extended_data': {}  # Will be filled by enrich_quote_row
                }
                transformed_rows.append(row)
            
            # Step 3: Apply FuturesTrading business logic - enrich with signals and classification
            enriched_rows = []
            for row in transformed_rows:
                # Apply signal classification logic to each quote
                enrich_quote_row(row)
                enriched_rows.append(row)
            
            # Step 4: Compute composite total with all classification logic
            total_data = compute_composite(enriched_rows)
            
            return Response({
                'rows': enriched_rows,
                'total': total_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in LatestQuotesView: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
