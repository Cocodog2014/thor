from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Subquery, OuterRef
from django.utils import timezone
from decimal import Decimal
import logging

from .models import TradingInstrument, MarketData, TradingSignal, SignalStatValue, ContractWeight
from .services.classification import enrich_quote_row, compute_composite

logger = logging.getLogger(__name__)

# TODO: Refactor to use LiveData/shared/redis_client.py instead of old provider factory
# TEMPORARY: Disabled until we restore Excel provider or implement TOS streaming
PROVIDER_AVAILABLE = False


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    """
    
    def get(self, request):
        try:
            # TODO: Implement LiveData integration
            # For now, return empty data until TOS streaming or Excel provider is restored
            raw_quotes = []
            
            if PROVIDER_AVAILABLE:
                # Old provider code would go here
                pass
            else:
                logger.warning("LatestQuotesView: No data provider available - returning empty data")
            
            # Step 2: Apply FuturesTrading business logic - enrich with signals and classification
            enriched_rows = []
            for quote in raw_quotes:
                # Apply signal classification logic to each quote
                enrich_quote_row(quote)
                enriched_rows.append(quote)
            
            # Step 3: Compute composite total with all classification logic
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
