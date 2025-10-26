"""
Market Open Capture Logic

Automatically captures futures market data when a global market opens.
Triggered by GlobalMarkets app when market status changes to OPEN.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
    """
    Captures all futures data at market open and creates session records.
    """
    
    # All futures to capture (11 instruments + TOTAL composite)
    FUTURES_SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
    
    def __init__(self):
        self.session_counter = None
    
    def get_next_session_number(self):
        """Get the next session number (sequential counter)"""
        last_session = MarketOpenSession.objects.order_by('-session_number').first()
        if last_session:
            return last_session.session_number + 1
        return 1
    
    def get_futures_data_from_redis(self, symbol):
        """
        Get current futures data from Redis.
        
        Args:
            symbol: Future symbol (YM, ES, NQ, etc.)
            
        Returns:
            dict: Futures data or None if not available
        """
        try:
            data = live_data_redis.get_latest_quote(symbol)
            if not data:
                logger.warning(f"No Redis data for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} from Redis: {e}")
            return None
    
    def calculate_total_composite(self, futures_data):
        """
        Calculate TOTAL composite signal from all 11 futures.
        
        Args:
            futures_data: Dict of symbol -> data
            
        Returns:
            dict: {
                'weighted_average': Decimal,
                'signal': str (BUY/SELL/STRONG_BUY/STRONG_SELL/HOLD),
                'sum_weighted': Decimal,
                'instrument_count': int
            }
        """
        total_weight = Decimal('0')
        sum_weighted = Decimal('0')
        count = 0
        
        for symbol, data in futures_data.items():
            if data and 'change_percent' in data:
                try:
                    # TODO: Fetch actual weight from ContractWeight model
                    weight = Decimal('1.0')
                    
                    change_pct = Decimal(str(data.get('change_percent', 0)))
                    weighted_value = change_pct * weight
                    
                    sum_weighted += weighted_value
                    total_weight += weight
                    count += 1
                    
                except Exception as e:
                    logger.warning(f"Error calculating weight for {symbol}: {e}")
        
        # Calculate weighted average
        if total_weight > 0:
            weighted_average = sum_weighted / total_weight
        else:
            weighted_average = Decimal('0')
        
        # Determine signal based on weighted average
        if weighted_average >= Decimal('0.5'):
            signal = 'STRONG_BUY'
        elif weighted_average >= Decimal('0.1'):
            signal = 'BUY'
        elif weighted_average <= Decimal('-0.5'):
            signal = 'STRONG_SELL'
        elif weighted_average <= Decimal('-0.1'):
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        return {
            'weighted_average': weighted_average,
            'signal': signal,
            'sum_weighted': sum_weighted,
            'instrument_count': count
        }
    
    def create_future_snapshot(self, session, symbol, data, is_total=False, total_data=None):
        """
        Create a FutureSnapshot record.
        
        Args:
            session: MarketOpenSession instance
            symbol: Future symbol
            data: Futures data from Redis
            is_total: True if this is the TOTAL composite snapshot
            total_data: TOTAL composite calculation results (for TOTAL snapshot)
            
        Returns:
            FutureSnapshot instance
        """
        try:
            snapshot_data = {
                'session': session,
                'symbol': symbol,
            }
            
            if is_total and total_data:
                # TOTAL composite snapshot
                snapshot_data.update({
                    'weighted_average': total_data['weighted_average'],
                    'signal': total_data['signal'],
                    'sum_weighted': total_data['sum_weighted'],
                    'instrument_count': total_data['instrument_count'],
                    'status': 'LIVE TOTAL',
                })
            else:
                # Regular future snapshot
                if data:
                    snapshot_data.update({
                        'last_price': Decimal(str(data.get('last', 0))) if data.get('last') else None,
                        'change': Decimal(str(data.get('change', 0))) if data.get('change') else None,
                        'change_percent': Decimal(str(data.get('change_percent', 0))) if data.get('change_percent') else None,
                        'bid': Decimal(str(data.get('bid', 0))) if data.get('bid') else None,
                        'bid_size': data.get('bid_size'),
                        'ask': Decimal(str(data.get('ask', 0))) if data.get('ask') else None,
                        'ask_size': data.get('ask_size'),
                        'volume': data.get('volume'),
                        'vwap': Decimal(str(data.get('vwap', 0))) if data.get('vwap') else None,
                        'open': Decimal(str(data.get('open', 0))) if data.get('open') else None,
                        'close': Decimal(str(data.get('close', 0))) if data.get('close') else None,
                        'day_24h_low': Decimal(str(data.get('low', 0))) if data.get('low') else None,
                        'day_24h_high': Decimal(str(data.get('high', 0))) if data.get('high') else None,
                        'week_52_low': Decimal(str(data.get('52_week_low', 0))) if data.get('52_week_low') else None,
                        'week_52_high': Decimal(str(data.get('52_week_high', 0))) if data.get('52_week_high') else None,
                    })
                    
                    # Calculate spread
                    if snapshot_data.get('bid') and snapshot_data.get('ask'):
                        snapshot_data['spread'] = snapshot_data['ask'] - snapshot_data['bid']
                    
                    # Calculate entry price and targets based on TOTAL signal
                    if total_data and total_data['signal'] not in ['HOLD']:
                        if total_data['signal'] in ['BUY', 'STRONG_BUY']:
                            snapshot_data['entry_price'] = snapshot_data.get('ask')
                        elif total_data['signal'] in ['SELL', 'STRONG_SELL']:
                            snapshot_data['entry_price'] = snapshot_data.get('bid')
                        
                        # Set targets (±20 points)
                        if snapshot_data.get('entry_price'):
                            snapshot_data['high_dynamic'] = snapshot_data['entry_price'] + 20
                            snapshot_data['low_dynamic'] = snapshot_data['entry_price'] - 20
                    
                    # Set signal for individual future
                    if total_data:
                        snapshot_data['signal'] = total_data['signal']
            
            snapshot = FutureSnapshot.objects.create(**snapshot_data)
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating snapshot for {symbol}: {e}", exc_info=True)
            return None
    
    @transaction.atomic
    def capture_market_open(self, market):
        """
        Main capture method - called when a market opens.
        
        Args:
            market: GlobalMarkets.Market instance
            
        Returns:
            MarketOpenSession instance or None if capture failed
        """
        try:
            logger.info(f"🎯 Capturing market open for {market.country}...")
            
            # Get market time info
            market_time = market.get_current_market_time()
            
            # Get next session number
            session_number = self.get_next_session_number()
            
            # Fetch all futures data from Redis
            futures_data = {}
            for symbol in self.FUTURES_SYMBOLS:
                data = self.get_futures_data_from_redis(symbol)
                if data:
                    futures_data[symbol] = data
            
            if not futures_data:
                logger.error(f"❌ No futures data available for {market.country} - cannot capture")
                return None
            
            # Calculate TOTAL composite
            total_composite = self.calculate_total_composite(futures_data)
            
            # Get YM data for session-level tracking
            ym_data = futures_data.get('YM')
            if not ym_data:
                logger.error(f"❌ No YM data available - cannot create session")
                return None
            
            # Create MarketOpenSession
            session_data = {
                'session_number': session_number,
                'year': market_time['year'],
                'month': market_time['month'],
                'date': market_time['date'],
                'day': market_time['day'],
                'country': market.country,
                'captured_at': timezone.now(),
                
                # YM price data
                'ym_open': Decimal(str(ym_data.get('open', 0))) if ym_data.get('open') else None,
                'ym_close': Decimal(str(ym_data.get('close', 0))) if ym_data.get('close') else None,
                'ym_ask': Decimal(str(ym_data.get('ask', 0))) if ym_data.get('ask') else None,
                'ym_bid': Decimal(str(ym_data.get('bid', 0))) if ym_data.get('bid') else None,
                'ym_last': Decimal(str(ym_data.get('last', 0))) if ym_data.get('last') else None,
                
                # TOTAL composite signal
                'total_signal': total_composite['signal'],
                'fw_weight': total_composite['weighted_average'],
                'study_fw': 'TOTAL',
            }
            
            # Auto-calculate entry and targets (handled by model.save())
            session = MarketOpenSession.objects.create(**session_data)
            logger.info(f"✅ Created session #{session_number} for {market.country} - Signal: {session.total_signal}")
            
            # Create snapshots for all 11 futures
            for symbol in self.FUTURES_SYMBOLS:
                data = futures_data.get(symbol)
                if data:
                    snapshot = self.create_future_snapshot(
                        session=session,
                        symbol=symbol,
                        data=data,
                        is_total=False,
                        total_data=total_composite
                    )
                    if snapshot:
                        logger.debug(f"  📊 Captured {symbol}: {snapshot.last_price}")
            
            # Create TOTAL composite snapshot
            total_snapshot = self.create_future_snapshot(
                session=session,
                symbol='TOTAL',
                data=None,
                is_total=True,
                total_data=total_composite
            )
            if total_snapshot:
                logger.info(f"  📊 TOTAL: {total_composite['weighted_average']:.4f} -> {total_composite['signal']}")
            
            logger.info(f"🎉 Market open capture complete for {market.country}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Error capturing market open for {market.country}: {e}", exc_info=True)
            return None


# Singleton instance
_capture_service = MarketOpenCaptureService()


def capture_market_open(market):
    """
    Public function to capture market open data.
    Called by GlobalMarkets when a market opens.
    
    Args:
        market: GlobalMarkets.Market instance
        
    Returns:
        MarketOpenSession instance or None
    """
    return _capture_service.capture_market_open(market)


__all__ = ['capture_market_open', 'MarketOpenCaptureService']
