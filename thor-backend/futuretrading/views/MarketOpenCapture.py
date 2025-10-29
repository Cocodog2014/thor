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
from FutureTrading.services.classification import enrich_quote_row, compute_composite
from FutureTrading.services.metrics import compute_row_metrics
from FutureTrading.models.extremes import Rolling52WeekStats

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
            # Map symbols that differ in Redis (e.g., DX stored as $DXY)
            redis_symbol_map = {
                'DX': '$DXY',
            }
            redis_key = redis_symbol_map.get(symbol, symbol)
            data = live_data_redis.get_latest_quote(redis_key)
            if not data:
                logger.warning(f"No Redis data for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} from Redis: {e}")
            return None
    
    def _build_enriched_rows(self, futures_data: dict) -> list[dict]:
        """Transform raw redis futures_data into enriched rows matching RTD flow."""
        # Load 52w stats from DB
        stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}

        rows = []
        symbol_map = {
            'RT': 'RTY',
            '30YrBond': 'ZB',
            '30Yr T-BOND': 'ZB',
            'T-BOND': 'ZB',
            '$DXY': 'DX',
            'DXY': 'DX',
            'USDX': 'DX',
        }

        for idx, sym in enumerate(self.FUTURES_SYMBOLS):
            data = futures_data.get(sym)
            if not data:
                continue
            raw_symbol = sym
            symbol = symbol_map.get(raw_symbol, raw_symbol)

            def to_str(val):
                return str(val) if val is not None else None

            sym_52w = stats_52w.get(symbol)
            high_52w = to_str(sym_52w.high_52w) if sym_52w else None
            low_52w = to_str(sym_52w.low_52w) if sym_52w else None

            row = {
                'instrument': {
                    'id': idx + 1,
                    'symbol': symbol,
                    'name': symbol,
                    'exchange': 'TOS',
                    'currency': 'USD',
                    'display_precision': 2,
                    'is_active': True,
                    'sort_order': idx
                },
                'price': to_str(data.get('last')),
                'last': to_str(data.get('last')),
                'bid': to_str(data.get('bid')),
                'ask': to_str(data.get('ask')),
                'volume': data.get('volume'),
                'open_price': to_str(data.get('open')),
                'high_price': to_str(data.get('high')),
                'low_price': to_str(data.get('low')),
                'close_price': to_str(data.get('close')),
                'previous_close': to_str(data.get('close')),
                'change': to_str(data.get('change')),
                'change_percent': None,
                'vwap': None,
                'bid_size': data.get('bid_size'),
                'ask_size': data.get('ask_size'),
                'extended_data': {
                    'high_52w': high_52w,
                    'low_52w': low_52w,
                },
            }
            # Enrich and compute metrics
            enrich_quote_row(row)
            try:
                metrics = compute_row_metrics(row)
                row.update(metrics)
                if row.get('change_percent') in (None, '', '—'):
                    row['change_percent'] = metrics.get('last_prev_pct')
            except Exception:
                pass
            rows.append(row)

        return rows
    
    def create_future_snapshot(self, session, symbol, data, is_total=False, total_data=None, enriched=None):
        """
        Create a FutureSnapshot record.
        
        Args:
            session: MarketOpenSession instance
            symbol: Future symbol
            data: Futures data from Redis
            is_total: True if this is the TOTAL composite snapshot
            total_data: TOTAL composite calculation results (for TOTAL snapshot)
            enriched: Enriched data with signal and weight from classification service
            
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
                    'weighted_average': total_data.get('weighted_average'),
                    'signal': total_data.get('signal'),
                    # For TOTAL, store the sum of signal weights and instrument count
                    'weight': int(total_data.get('signal_weight_sum')) if total_data.get('signal_weight_sum') is not None else None,
                    'sum_weighted': total_data.get('sum_weighted'),
                    'instrument_count': total_data.get('instrument_count'),
                    'status': 'LIVE TOTAL',
                })
            else:
                # Regular future snapshot
                if data:
                    snapshot_data.update({
                        'last_price': Decimal(str(data.get('last', 0))) if data.get('last') else None,
                        'change': Decimal(str(data.get('change', 0))) if data.get('change') else None,
                        # change_percent may not be provided by Redis; compute later if missing
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
                        # Prefer enriched 52w stats from DB; fall back to raw keys if present
                        'week_52_low': (
                            Decimal(str(enriched.get('low_52w'))) if (enriched and enriched.get('low_52w') is not None)
                            else (Decimal(str(data.get('low_52w'))) if data.get('low_52w') is not None
                                  else (Decimal(str(data.get('52_week_low'))) if data.get('52_week_low') is not None else None))
                        ),
                        'week_52_high': (
                            Decimal(str(enriched.get('high_52w'))) if (enriched and enriched.get('high_52w') is not None)
                            else (Decimal(str(data.get('high_52w'))) if data.get('high_52w') is not None
                                  else (Decimal(str(data.get('52_week_high'))) if data.get('52_week_high') is not None else None))
                        ),
                        # Use ENRICHED signal and weight from classification service
                        'signal': enriched.get('signal') if enriched else None,
                        'weight': (int(enriched.get('signal_weight')) if (enriched and enriched.get('signal_weight') is not None) else None),
                    })
                    
                    # Calculate spread
                    if snapshot_data.get('bid') and snapshot_data.get('ask'):
                        snapshot_data['spread'] = snapshot_data['ask'] - snapshot_data['bid']
                    
                    # Derive metrics the RTD card shows when not present in raw data
                    # 1) change_percent = change / close * 100
                    if (not snapshot_data.get('change_percent')
                        and snapshot_data.get('change') is not None
                        and snapshot_data.get('close') not in (None, 0)):
                        try:
                            snapshot_data['change_percent'] = (snapshot_data['change'] / snapshot_data['close']) * Decimal('100')
                        except Exception:
                            pass

                    # 2) Open vs Prev (number and percent)
                    if snapshot_data.get('open') is not None and snapshot_data.get('close') is not None:
                        try:
                            diff = snapshot_data['open'] - snapshot_data['close']
                            snapshot_data['open_vs_prev_number'] = diff
                            if snapshot_data['close'] not in (None, 0):
                                snapshot_data['open_vs_prev_percent'] = (diff / snapshot_data['close']) * Decimal('100')
                        except Exception:
                            pass

                    # 3) 24h Range and range percent
                    if snapshot_data.get('day_24h_high') is not None and snapshot_data.get('day_24h_low') is not None:
                        try:
                            rng = snapshot_data['day_24h_high'] - snapshot_data['day_24h_low']
                            snapshot_data['range_high_low'] = rng
                            if snapshot_data.get('close') not in (None, 0):
                                snapshot_data['range_percent'] = (rng / snapshot_data['close']) * Decimal('100')
                        except Exception:
                            pass

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
            
            # Fetch all futures data from Redis, then transform and enrich like RTD
            futures_data = {}
            for symbol in self.FUTURES_SYMBOLS:
                data = self.get_futures_data_from_redis(symbol)
                if data:
                    futures_data[symbol] = data
            
            if not futures_data:
                logger.error(f"❌ No futures data available for {market.country} - cannot capture")
                return None
            
            # Build enriched rows and compute composite
            enriched_rows = self._build_enriched_rows(futures_data)
            total_comp = compute_composite(enriched_rows)
            
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
                
                # TOTAL composite signal (aligned with RTD compute)
                'total_signal': total_comp.get('composite_signal') or 'HOLD',
                'fw_weight': Decimal(str(total_comp.get('avg_weighted'))) if total_comp.get('avg_weighted') else Decimal('0'),
                'study_fw': 'TOTAL',
            }
            
            # Auto-calculate entry and targets (handled by model.save())
            session = MarketOpenSession.objects.create(**session_data)
            logger.info(f"✅ Created session #{session_number} for {market.country} - Signal: {session.total_signal}")
            
            # Create snapshots for all 11 futures using enriched rows
            for row in enriched_rows:
                symbol = row['instrument']['symbol']
                data = futures_data.get(symbol)
                enriched = row.get('extended_data', {})
                if data:
                    snapshot = self.create_future_snapshot(
                        session=session,
                        symbol=symbol,
                        data=data,
                        is_total=False,
                        total_data={
                            'signal': session.total_signal
                        },
                        enriched=enriched
                    )
                    if snapshot:
                        logger.debug(f"  📊 Captured {symbol}: {snapshot.last_price}")
            
            # Create TOTAL composite snapshot (map RTD compute fields)
            total_snapshot = self.create_future_snapshot(
                session=session,
                symbol='TOTAL',
                data=None,
                is_total=True,
                total_data={
                    'weighted_average': Decimal(str(total_comp.get('avg_weighted'))) if total_comp.get('avg_weighted') else Decimal('0'),
                    'signal': total_comp.get('composite_signal') or 'HOLD',
                    'sum_weighted': Decimal(str(total_comp.get('sum_weighted'))) if total_comp.get('sum_weighted') else Decimal('0'),
                    'instrument_count': total_comp.get('count') or len(self.FUTURES_SYMBOLS),
                    'signal_weight_sum': total_comp.get('signal_weight_sum')
                }
            )
            if total_snapshot:
                try:
                    wa = Decimal(str(total_comp.get('avg_weighted'))) if total_comp.get('avg_weighted') else Decimal('0')
                    sig = total_comp.get('composite_signal') or 'HOLD'
                    logger.info(f"  📊 TOTAL: {wa:.4f} -> {sig}")
                except Exception:
                    logger.info("  📊 TOTAL snapshot created")
            
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
