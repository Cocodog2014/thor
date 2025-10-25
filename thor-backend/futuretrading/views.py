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
from .services.metrics import compute_row_metrics
from .config import TOS_EXCEL_FILE, TOS_EXCEL_SHEET, TOS_EXCEL_RANGE

logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    
    Now uses LiveData/tos endpoint to get TOS RTD Excel data.
    """
    
    def get(self, request):
        try:
            # Step 1: Get raw quotes from LiveData snapshot (provider-agnostic)
            raw_quotes = []
            
            try:
                # Build symbols list for snapshot
                symbols = ','.join([
                    'YM','ES','NQ','RTY','CL','SI','HG','GC','VX','DX','ZB'
                ])
                # Call generic snapshot endpoint (reads from Redis cache)
                response = requests.get(
                    'http://localhost:8000/api/feed/quotes/snapshot/',
                    params={'symbols': symbols, 'consumer': 'futures_trading'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    raw_quotes = data.get('quotes', [])
                    logger.info(f"Fetched {len(raw_quotes)} quotes from Redis snapshot")
                else:
                    logger.warning(f"TOS endpoint returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch TOS data: {e}")
            
            # Step 2: Transform TOS quotes into FutureTrading structure (instrument + fields)
            transformed_rows = []
            for idx, quote in enumerate(raw_quotes):
                raw_symbol = quote.get('symbol', '')
                
                # Normalize symbol - fix common Excel RTD symbol mismatches
                # RT -> RTY (Russell 2000 correct symbol)
                # 30YrBond -> ZB (30-Year Treasury Bond)
                symbol_map = {
                    'RT': 'RTY',
                    '30YrBond': 'ZB',
                    '30Yr T-BOND': 'ZB',
                    'T-BOND': 'ZB',
                }
                symbol = symbol_map.get(raw_symbol, raw_symbol)
                
                # Convert Decimal/float to string for JSON serialization
                def to_str(val):
                    return str(val) if val is not None else None
                
                # Wrap quote data in expected MarketData structure
                row = {
                    'instrument': {
                        'id': idx + 1,
                        'symbol': symbol,  # Use normalized symbol
                        'name': symbol,
                        'exchange': 'TOS',
                        'currency': 'USD',
                        'display_precision': 2,
                        'is_active': True,
                        'sort_order': idx
                    },
                    # Frontend expects these field names
                    'price': to_str(quote.get('last')),  # Frontend calls it 'price', not 'last'
                    'last': to_str(quote.get('last')),   # Also keep 'last' for compatibility
                    'bid': to_str(quote.get('bid')),
                    'ask': to_str(quote.get('ask')),
                    'volume': quote.get('volume'),
                    'open_price': to_str(quote.get('open')),
                    'high_price': to_str(quote.get('high')),
                    'low_price': to_str(quote.get('low')),
                    'close_price': to_str(quote.get('close')),
                    'previous_close': to_str(quote.get('close')),  # Previous close = close
                    'change': to_str(quote.get('change')),
                    'change_percent': None,  # Could calculate if needed
                    'vwap': None,  # Not available in TOS RTD basic data
                    'bid_size': quote.get('bid_size'),
                    'ask_size': quote.get('ask_size'),
                    'last_size': None,
                    'market_status': 'CLOSED',  # Would need market hours logic
                    'data_source': 'TOS_RTD',
                    'is_real_time': True,
                    'delay_minutes': 0,
                    'timestamp': quote.get('timestamp'),
                    'extended_data': {}  # Will be filled by enrich_quote_row
                }
                transformed_rows.append(row)
            
            # Step 3: Apply FuturesTrading business logic - enrich with signals and classification
            enriched_rows = []
            for row in transformed_rows:
                # Apply signal classification logic to each quote
                enrich_quote_row(row)
                # Compute derived numeric metrics and attach
                try:
                    metrics = compute_row_metrics(row)
                    row.update(metrics)
                    # If change_percent is not provided, align it with last vs prev close
                    if row.get('change_percent') in (None, '', '—'):
                        row['change_percent'] = metrics.get('last_prev_pct')
                except Exception as e:
                    logger.warning(f"Metric computation failed for {row.get('instrument',{}).get('symbol','?')}: {e}")
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
