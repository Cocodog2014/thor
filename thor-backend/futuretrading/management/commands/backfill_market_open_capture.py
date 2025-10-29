from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any
import logging

from FutureTrading.models import MarketOpenSession, FutureSnapshot, TradingInstrument
from FutureTrading.config import EXPECTED_FUTURES
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.services.classification import enrich_quote_row, compute_composite
from FutureTrading.services.metrics import compute_row_metrics
from FutureTrading.models.extremes import Rolling52WeekStats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill a MarketOpenSession's FutureSnapshot fields by enriching from latest Redis quotes.\n"
        "Updates per-future signal, weight, last/change/change%, 24h/52w ranges, open_vs_prev, spread, and TOTAL composite."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=int,
            help="Specific MarketOpenSession ID to backfill (default: latest by captured_at)",
        )
        parser.add_argument(
            "--country",
            type=str,
            help="Filter to a specific country (if multiple sessions exist today)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute and log updates without writing to the database",
        )

    def handle(self, *args, **options):
        session_id = options.get("session_id")
        country = options.get("country")
        dry_run = options.get("dry_run")

        qs = MarketOpenSession.objects.all()
        if country:
            qs = qs.filter(country__iexact=country)
        if session_id:
            qs = qs.filter(id=session_id)
        session = qs.order_by("-captured_at").first()

        if not session:
            raise CommandError("No MarketOpenSession found with the specified criteria.")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Backfilling session id={session.id} country={session.country} captured={session.captured_at}"
        ))

        # Prepare instruments and 52w stats
        instruments_db = {inst.symbol: inst for inst in TradingInstrument.objects.all()}
        stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}

        # Map canonical to redis symbols
        redis_symbol_map = {
            'DX': '$DXY',
        }
        fetch_symbols = [redis_symbol_map.get(sym, sym) for sym in EXPECTED_FUTURES]

        # Fetch latest from Redis
        raw_quotes = live_data_redis.get_latest_quotes(fetch_symbols) or []
        if not raw_quotes:
            self.stdout.write(self.style.WARNING("No quotes found in Redis. Is the Excel poller running?"))

        # Normalize by canonical symbol
        symbol_map = {
            'RT': 'RTY',
            '30YrBond': 'ZB',
            '30Yr T-BOND': 'ZB',
            'T-BOND': 'ZB',
            '$DXY': 'DX',
            'DXY': 'DX',
            'USDX': 'DX',
        }

        # Build transformed rows similar to RTD view
        transformed_rows = []
        for idx, quote in enumerate(raw_quotes):
            raw_symbol = quote.get('symbol', '')
            symbol = symbol_map.get(raw_symbol, raw_symbol)
            db_inst = instruments_db.get(symbol) or instruments_db.get(f'/{symbol}')
            display_precision = db_inst.display_precision if db_inst else 2
            tick_value = str(db_inst.tick_value) if db_inst and db_inst.tick_value else None
            margin_requirement = str(db_inst.margin_requirement) if db_inst and db_inst.margin_requirement else None

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
                    'display_precision': display_precision,
                    'tick_value': tick_value,
                    'margin_requirement': margin_requirement,
                    'is_active': True,
                    'sort_order': idx
                },
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
                'last_size': None,
                'market_status': 'CLOSED',
                'data_source': 'TOS_RTD',
                'is_real_time': True,
                'delay_minutes': 0,
                'timestamp': quote.get('timestamp'),
                'extended_data': {
                    'high_52w': high_52w,
                    'low_52w': low_52w,
                }
            }
            try:
                enrich_quote_row(row)
                metrics = compute_row_metrics(row)
                row.update(metrics)
                if row.get('change_percent') in (None, '', '—'):
                    row['change_percent'] = metrics.get('last_prev_pct')
            except Exception as e:
                logger.warning(f"Enrichment failed for {symbol}: {e}")
            transformed_rows.append(row)

        # Index enriched rows by symbol
        by_symbol: Dict[str, Dict[str, Any]] = {r['instrument']['symbol']: r for r in transformed_rows}

        # Compute composite from enriched rows
        try:
            total_data = compute_composite(list(by_symbol.values()))
        except Exception as e:
            logger.warning(f"Composite computation failed: {e}")
            total_data = None

        # Write updates
        @transaction.atomic
        def do_update():
            updated = 0
            futures_qs = session.futures.all()
            for snap in futures_qs:
                if snap.symbol == 'TOTAL':
                    if not total_data:
                        continue
                    prev = (snap.weighted_average, snap.sum_weighted, snap.instrument_count, snap.signal, snap.weight)
                    # Map RTD compute fields
                    snap.weighted_average = safe_decimal(total_data.get('avg_weighted'))
                    snap.sum_weighted = safe_decimal(total_data.get('sum_weighted'))
                    snap.instrument_count = total_data.get('count') or 11
                    snap.signal = (total_data.get('composite_signal') or '').upper()
                    # Derive TOTAL weight as int(sum of per-row signal_weight)
                    try:
                        total_weight = int(round(sum(int_row_weight(r) for r in by_symbol.values())))
                    except Exception:
                        total_weight = None
                    snap.weight = total_weight
                    if prev != (snap.weighted_average, snap.sum_weighted, snap.instrument_count, snap.signal, snap.weight):
                        updated += 1
                        snap.save(update_fields=['weighted_average', 'sum_weighted', 'instrument_count', 'signal', 'weight'])
                    continue

                row = by_symbol.get(snap.symbol)
                if not row:
                    continue

                prev = (
                    snap.last_price, snap.change, snap.change_percent, snap.signal, snap.weight,
                    snap.bid, snap.ask, snap.bid_size, snap.ask_size, snap.volume, snap.vwap,
                    snap.open, snap.close, snap.open_vs_prev_number, snap.open_vs_prev_percent,
                    snap.day_24h_low, snap.day_24h_high, snap.range_high_low, snap.range_percent,
                    snap.week_52_low, snap.week_52_high, snap.week_52_range_high_low, snap.week_52_range_percent,
                    snap.spread
                )

                # Basic price + deltas
                snap.last_price = safe_decimal(row.get('last'))
                snap.change = safe_decimal(row.get('change'))
                snap.change_percent = safe_decimal(row.get('change_percent'))

                # Signal + weight
                ext = (row.get('extended_data') or {})
                snap.signal = (ext.get('signal') or '').upper()
                # Prefer signal_weight; fallback to contract_weight if present
                weight = ext.get('signal_weight') if ext.get('signal_weight') is not None else ext.get('contract_weight')
                snap.weight = int(weight) if weight is not None else None

                # Bid/Ask/Volume, spread
                snap.bid = safe_decimal(row.get('bid'))
                snap.ask = safe_decimal(row.get('ask'))
                snap.bid_size = to_int(row.get('bid_size'))
                snap.ask_size = to_int(row.get('ask_size'))
                snap.volume = to_int(row.get('volume'))
                snap.vwap = safe_decimal(row.get('vwap'))
                snap.spread = (snap.ask - snap.bid) if (snap.ask is not None and snap.bid is not None) else None

                # Session open/close and derived
                snap.open = safe_decimal(row.get('open_price'))
                snap.close = safe_decimal(row.get('close_price'))
                if snap.open is not None and snap.close is not None:
                    snap.open_vs_prev_number = (snap.open - snap.close)
                    try:
                        snap.open_vs_prev_percent = (snap.open - snap.close) / snap.close * Decimal('100')
                    except Exception:
                        snap.open_vs_prev_percent = None

                # 24h range
                snap.day_24h_low = safe_decimal(row.get('low_price'))
                snap.day_24h_high = safe_decimal(row.get('high_price'))
                if snap.day_24h_high is not None and snap.day_24h_low is not None:
                    snap.range_high_low = (snap.day_24h_high - snap.day_24h_low)
                    try:
                        prev_close = snap.close if snap.close is not None else safe_decimal(row.get('previous_close'))
                        snap.range_percent = (snap.range_high_low / prev_close * Decimal('100')) if prev_close else None
                    except Exception:
                        snap.range_percent = None

                # 52w stats
                ext = (row.get('extended_data') or {})
                snap.week_52_high = safe_decimal(ext.get('high_52w'))
                snap.week_52_low = safe_decimal(ext.get('low_52w'))
                if snap.week_52_high is not None and snap.week_52_low is not None:
                    snap.week_52_range_high_low = (snap.week_52_high - snap.week_52_low)
                    try:
                        curr = snap.last_price if snap.last_price is not None else snap.close
                        snap.week_52_range_percent = (snap.week_52_range_high_low / curr * Decimal('100')) if curr else None
                    except Exception:
                        snap.week_52_range_percent = None

                new_state = (
                    snap.last_price, snap.change, snap.change_percent, snap.signal, snap.weight,
                    snap.bid, snap.ask, snap.bid_size, snap.ask_size, snap.volume, snap.vwap,
                    snap.open, snap.close, snap.open_vs_prev_number, snap.open_vs_prev_percent,
                    snap.day_24h_low, snap.day_24h_high, snap.range_high_low, snap.range_percent,
                    snap.week_52_low, snap.week_52_high, snap.week_52_range_high_low, snap.week_52_range_percent,
                    snap.spread
                )

                if new_state != prev:
                    snap.save(update_fields=[
                        'last_price','change','change_percent','signal','weight',
                        'bid','ask','bid_size','ask_size','volume','vwap','spread',
                        'open','close','open_vs_prev_number','open_vs_prev_percent',
                        'day_24h_low','day_24h_high','range_high_low','range_percent',
                        'week_52_low','week_52_high','week_52_range_high_low','week_52_range_percent',
                    ])
                    updated += 1

            return updated

        if dry_run:
            self.stdout.write(self.style.HTTP_INFO("Dry-run: computed updates; no database writes performed."))
            return

        updated = do_update()
        self.stdout.write(self.style.SUCCESS(f"Backfill complete. Updated {updated} snapshot(s)."))


def safe_decimal(val: Any) -> Optional[Decimal]:
    if val is None or val == '' or val == '—':
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def to_int(val: Any) -> Optional[int]:
    if val is None or val == '' or val == '—':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        try:
            return int(float(val))
        except Exception:
            return None


def int_row_weight(row: Dict[str, Any]) -> int:
    ext = (row.get('extended_data') or {})
    w = ext.get('signal_weight') if ext.get('signal_weight') is not None else ext.get('contract_weight')
    try:
        return int(w) if w is not None else 0
    except Exception:
        try:
            return int(float(w)) if w is not None else 0
        except Exception:
            return 0
