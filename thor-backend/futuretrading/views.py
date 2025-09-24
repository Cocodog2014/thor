from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Subquery, OuterRef
from django.utils import timezone
from decimal import Decimal
import logging

from .models import TradingInstrument, MarketData, TradingSignal, SignalStatValue, ContractWeight


logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    """
    
    def get(self, request):
        try:
            # Get all active futures instruments
            instruments = TradingInstrument.objects.filter(
                is_active=True,
                category__name='futures'  # Assuming futures category exists
            ).select_related('category')
            
            rows = []
            weighted_sum = Decimal('0.0')
            total_weights = Decimal('0.0')
            
            for instrument in instruments:
                # Get latest market data
                latest_market_data = MarketData.objects.filter(
                    instrument=instrument
                ).order_by('-timestamp').first()
                
                # Get latest trading signal
                latest_signal = TradingSignal.objects.filter(
                    instrument=instrument
                ).order_by('-created_at').first()
                
                # Get statistical value for this instrument/signal combination
                stat_value = None
                if latest_signal:
                    try:
                        signal_stat = SignalStatValue.objects.get(
                            instrument=instrument,
                            signal=latest_signal.signal
                        )
                        stat_value = signal_stat.value
                    except SignalStatValue.DoesNotExist:
                        stat_value = None
                
                # Get contract weight
                contract_weight = Decimal('1.0')  # Default weight
                try:
                    weight_obj = ContractWeight.objects.get(instrument=instrument)
                    contract_weight = weight_obj.weight
                except ContractWeight.DoesNotExist:
                    pass
                
                # Build extended_data
                extended_data = {}
                if latest_signal:
                    extended_data['signal'] = latest_signal.signal
                if stat_value is not None:
                    extended_data['stat_value'] = str(stat_value)
                    # Add to weighted total
                    weighted_sum += stat_value * contract_weight
                    total_weights += abs(contract_weight)
                extended_data['contract_weight'] = str(contract_weight)
                
                # Build row data
                row = {
                    'instrument': {
                        'id': instrument.id,
                        'symbol': instrument.symbol,
                        'name': instrument.name,
                        'exchange': instrument.exchange,
                        'currency': instrument.currency,
                        'category': instrument.category.name if instrument.category else None,
                        # Add fields used by the frontend L1 cards for formatting/order
                        'display_precision': instrument.display_precision,
                        'is_active': instrument.is_active,
                        'sort_order': instrument.sort_order,
                    }
                }
                
                # Add market data if available
                if latest_market_data:
                    row.update({
                        'price': str(latest_market_data.price),
                        'bid': str(latest_market_data.bid) if latest_market_data.bid else None,
                        'ask': str(latest_market_data.ask) if latest_market_data.ask else None,
                        'bid_size': latest_market_data.bid_size,
                        'ask_size': latest_market_data.ask_size,
                        'open_price': str(latest_market_data.open_price) if latest_market_data.open_price else None,
                        'high_price': str(latest_market_data.high_price) if latest_market_data.high_price else None,
                        'low_price': str(latest_market_data.low_price) if latest_market_data.low_price else None,
                        'previous_close': str(latest_market_data.previous_close) if latest_market_data.previous_close else None,
                        'change': str(latest_market_data.change) if latest_market_data.change else None,
                        'change_percent': str(latest_market_data.change_percent) if latest_market_data.change_percent else None,
                        'vwap': latest_market_data.vwap,
                        'volume': latest_market_data.volume,
                        'market_status': latest_market_data.market_status,
                        'data_source': latest_market_data.data_source,
                        'is_real_time': latest_market_data.is_real_time,
                        'delay_minutes': latest_market_data.delay_minutes,
                        'timestamp': latest_market_data.timestamp.isoformat() if latest_market_data.timestamp else None,
                    })
                else:
                    # No market data available
                    row.update({
                        'price': None,
                        'bid': None,
                        'ask': None,
                        'bid_size': None,
                        'ask_size': None,
                        'open_price': None,
                        'high_price': None,
                        'low_price': None,
                        'previous_close': None,
                        'change': None,
                        'change_percent': None,
                        'vwap': None,
                        'volume': None,
                        'market_status': 'UNKNOWN',
                        'data_source': None,
                        'is_real_time': False,
                        'delay_minutes': 0,
                        'timestamp': None,
                    })
                
                row['extended_data'] = extended_data
                rows.append(row)
            
            # Calculate total composite
            avg_weighted = None
            if total_weights > 0:
                avg_weighted = weighted_sum / total_weights
            
            total_data = {
                'sum_weighted': str(weighted_sum),
                'avg_weighted': str(avg_weighted) if avg_weighted is not None else None,
                'count': len(rows),
                'denominator': str(total_weights),
                'as_of': timezone.now().isoformat(),
            }
            
            return Response({
                'rows': rows,
                'total': total_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in LatestQuotesView: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
