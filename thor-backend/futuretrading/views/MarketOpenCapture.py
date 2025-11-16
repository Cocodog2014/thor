"""
Market Open Capture - Clean Implementation

Captures futures data at market open using the same enrichment pipeline as the live RTD endpoint.
Single path, no legacy code, fully traceable.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot
from FutureTrading.models.extremes import Rolling52WeekStats
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.services.classification import enrich_quote_row, compute_composite
from FutureTrading.services.metrics import compute_row_metrics

logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
    """Captures futures data at market open - matches RTD endpoint logic exactly"""
    
    FUTURES_SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
    REDIS_SYMBOL_MAP = {'DX': '$DXY'}
    SYMBOL_NORMALIZE_MAP = {
        'RT': 'RTY', '30YrBond': 'ZB', '30Yr T-BOND': 'ZB', 'T-BOND': 'ZB',
        '$DXY': 'DX', 'DXY': 'DX', 'USDX': 'DX'
    }
    
    def get_next_session_number(self):
        last = MarketOpenSession.objects.order_by('-session_number').first()
        return (last.session_number + 1) if last else 1
    
    def fetch_redis_quotes(self):
        quotes = {}
        for symbol in self.FUTURES_SYMBOLS:
            key = self.REDIS_SYMBOL_MAP.get(symbol, symbol)
            try:
                data = live_data_redis.get_latest_quote(key)
                if data:
                    quotes[symbol] = data
            except Exception as e:
                logger.error(f"Redis fetch failed for {symbol}: {e}")
        return quotes
    
    def build_enriched_rows(self, redis_quotes):
        stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}
        rows = []
        
        for idx, symbol in enumerate(self.FUTURES_SYMBOLS):
            quote = redis_quotes.get(symbol)
            if not quote:
                continue
            
            norm_sym = self.SYMBOL_NORMALIZE_MAP.get(symbol, symbol)
            sym_52w = stats_52w.get(norm_sym)
            
            to_str = lambda v: str(v) if v is not None else None
            
            row = {
                'instrument': {'id': idx+1, 'symbol': norm_sym, 'name': norm_sym, 'exchange': 'TOS', 
                              'currency': 'USD', 'display_precision': 2, 'is_active': True, 'sort_order': idx},
                'price': to_str(quote.get('last')),
                'last': to_str(quote.get('last')),
                'bid': to_str(quote.get('bid')),
                'ask': to_str(quote.get('ask')),
                'volume': quote.get('volume'),
                'open_price': to_str(quote.get('open')),
                'high_price': to_str(quote.get('high')),
                'low_price': to_str(quote.get('low')),
                'close_price': to_str(quote.get('close')),
                'previous_close': to_str(quote.get('close')),
                'change': to_str(quote.get('change')),
                'change_percent': None,
                'vwap': None,
                'bid_size': quote.get('bid_size'),
                'ask_size': quote.get('ask_size'),
                'extended_data': {
                    'high_52w': str(sym_52w.high_52w) if (sym_52w and sym_52w.high_52w) else None,
                    'low_52w': str(sym_52w.low_52w) if (sym_52w and sym_52w.low_52w) else None
                }
            }
            
            enrich_quote_row(row)
            try:
                metrics = compute_row_metrics(row)
                row.update(metrics)
                if row.get('change_percent') in (None, '', ''):
                    row['change_percent'] = metrics.get('last_prev_pct')
            except Exception as e:
                logger.warning(f"Metrics failed for {norm_sym}: {e}")
            
            rows.append(row)
        return rows
    
    def safe_decimal(self, val):
        if val in (None, '', ''):
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None
    
    def safe_int(self, val):
        if val in (None, '', ''):
            return None
        try:
            return int(val)
        except Exception:
            try:
                return int(float(val))
            except Exception:
                return None
    
    def create_future_snapshots(self, session, enriched_rows, total_signal):
        snapshots = []
        for row in enriched_rows:
            symbol = row['instrument']['symbol']
            ext = row.get('extended_data', {})
            
            data = {
                'session': session,
                'symbol': symbol,
                'last_price': self.safe_decimal(row.get('last')),
                'change': self.safe_decimal(row.get('change')),
                'change_percent': self.safe_decimal(row.get('change_percent') or row.get('last_prev_pct')),
                'bid': self.safe_decimal(row.get('bid')),
                'bid_size': self.safe_int(row.get('bid_size')),
                'ask': self.safe_decimal(row.get('ask')),
                'ask_size': self.safe_int(row.get('ask_size')),
                'volume': self.safe_int(row.get('volume')),
                'vwap': self.safe_decimal(row.get('vwap')),
                'spread': self.safe_decimal(row.get('spread')),
                'open': self.safe_decimal(row.get('open_price')),
                'close': self.safe_decimal(row.get('close_price') or row.get('previous_close')),
                'open_vs_prev_number': self.safe_decimal(row.get('open_prev_diff')),
                'open_vs_prev_percent': self.safe_decimal(row.get('open_prev_pct')),
                'day_24h_low': self.safe_decimal(row.get('low_price')),
                'day_24h_high': self.safe_decimal(row.get('high_price')),
                'range_high_low': self.safe_decimal(row.get('range_diff')),
                'range_percent': self.safe_decimal(row.get('range_pct')),
                'week_52_low': self.safe_decimal(ext.get('low_52w')),
                'week_52_high': self.safe_decimal(ext.get('high_52w')),
                'signal': (ext.get('signal') or '').upper() if ext.get('signal') else '',
                'weight': self.safe_int(ext.get('signal_weight'))
            }
            
            if total_signal and total_signal not in ['HOLD', '']:
                if total_signal in ['BUY', 'STRONG_BUY']:
                    data['entry_price'] = data.get('ask')
                elif total_signal in ['SELL', 'STRONG_SELL']:
                    data['entry_price'] = data.get('bid')
                if data.get('entry_price'):
                    data['high_dynamic'] = data['entry_price'] + 20
                    data['low_dynamic'] = data['entry_price'] - 20
            
            try:
                snap = FutureSnapshot.objects.create(**data)
                snapshots.append(snap)
                logger.debug(f"Captured {symbol}: {snap.last_price}")
            except Exception as e:
                logger.error(f"Snapshot failed for {symbol}: {e}", exc_info=True)
        return snapshots
    
    def create_total_snapshot(self, session, composite):
        data = {
            'session': session,
            'symbol': 'TOTAL',
            'weighted_average': self.safe_decimal(composite.get('avg_weighted')),
            'sum_weighted': self.safe_decimal(composite.get('sum_weighted')),
            'instrument_count': composite.get('count') or 11,
            'signal': (composite.get('composite_signal') or 'HOLD').upper(),
            'weight': composite.get('signal_weight_sum'),
            'status': 'LIVE TOTAL'
        }
        try:
            snap = FutureSnapshot.objects.create(**data)
            logger.info(f"TOTAL: {data['weighted_average']:.4f} -> {data['signal']}" if data['weighted_average'] else f"TOTAL: {data['signal']}")
            return snap
        except Exception as e:
            logger.error(f"TOTAL snapshot failed: {e}", exc_info=True)
            return None
    
    @transaction.atomic
    def capture_market_open(self, market):
        try:
            logger.info(f"Capturing {market.country} market open...")
            
            redis_quotes = self.fetch_redis_quotes()
            if not redis_quotes:
                logger.error(f"No quotes for {market.country}")
                return None
            
            enriched = self.build_enriched_rows(redis_quotes)
            if not enriched:
                logger.error(f"No enriched rows for {market.country}")
                return None
            
            composite = compute_composite(enriched)
            ym = redis_quotes.get('YM')
            if not ym:
                logger.error("No YM data")
                return None
            
            time_info = market.get_current_market_time()
            
            session = MarketOpenSession.objects.create(
                session_number=self.get_next_session_number(),
                year=time_info['year'],
                month=time_info['month'],
                date=time_info['date'],
                day=time_info['day'],
                country=market.country,
                captured_at=timezone.now(),
                ym_open=self.safe_decimal(ym.get('open')),
                ym_close=self.safe_decimal(ym.get('close')),
                ym_ask=self.safe_decimal(ym.get('ask')),
                ym_bid=self.safe_decimal(ym.get('bid')),
                ym_last=self.safe_decimal(ym.get('last')),
                total_signal=composite.get('composite_signal') or 'HOLD',
                fw_weight=self.safe_decimal(composite.get('avg_weighted')) or Decimal('0'),
                study_fw='TOTAL'
            )
            
            logger.info(f"Session #{session.session_number} created - {session.total_signal}")
            
            snaps = self.create_future_snapshots(session, enriched, session.total_signal)
            total = self.create_total_snapshot(session, composite)
            
            logger.info(f"Capture complete: {len(snaps)} futures + TOTAL")
            return session
            
        except Exception as e:
            logger.error(f"Capture failed for {market.country}: {e}", exc_info=True)
            return None


_service = MarketOpenCaptureService()

def capture_market_open(market):
    return _service.capture_market_open(market)

__all__ = ['capture_market_open', 'MarketOpenCaptureService']
