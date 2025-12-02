from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse, HttpRequest
from django.utils.timezone import now
import json
import time
from .redis_client import get_redis, latest_key, unified_stream_key
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from account_statement.models.paper import PaperAccount
from account_statement.models.real import RealAccount
from decimal import Decimal
from ThorTrading.services.vwap import vwap_service
from LiveData.shared.redis_client import live_data_redis
from django.db import connection

@api_view(['GET'])
def session(request: HttpRequest):
    """
    GET /api/session?market=Tokyo&future=YM

    Returns session payload including latest 1-minute intraday bar for the
    given market (market_code) and future symbol from table `intraday_1m`.

    Response shape (partial):
    {
      "market": "Tokyo",
      "future": "YM",
      "intraday_latest": {
        "open": float | null,
        "high": float | null,
        "low": float | null,
        "close": float | null,
        "volume": int | null,
        "spread": float | null
      }
    }
    """
    market_code = (request.GET.get('market') or '').strip()
    future = (request.GET.get('future') or '').strip().upper()

    if not market_code or not future:
        return Response({
            'detail': 'Both market and future parameters are required.',
            'market': market_code,
            'future': future,
            'intraday_latest': None,
        }, status=status.HTTP_400_BAD_REQUEST)

    # Query latest 1-minute bar
    sql = (
        """
        SELECT open_1m, high_1m, low_1m, close_1m, volume_1m, spread_last
        FROM intraday_1m
        WHERE market_code = %s AND future = %s
        ORDER BY timestamp_minute DESC
        LIMIT 1
        """
    )

    latest = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, [market_code, future])
            row = cursor.fetchone()
            if row:
                open_v, high_v, low_v, close_v, volume_v, spread_v = row
                latest = {
                    'open': float(open_v) if open_v is not None else None,
                    'high': float(high_v) if high_v is not None else None,
                    'low': float(low_v) if low_v is not None else None,
                    'close': float(close_v) if close_v is not None else None,
                    'volume': int(volume_v) if volume_v is not None else None,
                    'spread': float(spread_v) if spread_v is not None else None,
                }
    except Exception as e:
        return Response({'detail': f'Database error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Minimal payload; hooks exist to merge session tiles when available
    payload = {
        'market': market_code,
        'future': future,
        'intraday_latest': latest,
    }

    return Response(payload, status=status.HTTP_200_OK)

@api_view(['GET'])
def vwap_today(request: HttpRequest):
    """GET /api/vwap/today?symbols=ES,YM

    Returns current session VWAP for requested comma-separated symbols.
    If symbols param omitted returns empty list. VWAP values may be null
    if insufficient data (no rows yet).
    Response shape: [{symbol, vwap, as_of}] with vwap as string or null.
    """
    symbols_param = request.GET.get('symbols') or ''
    symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
    out = []
    now_iso = now().isoformat()
    for sym in symbols:
        try:
            val = vwap_service.get_today_vwap(sym)
            out.append({
                'symbol': sym,
                'vwap': f"{val}" if val is not None else None,
                'as_of': now_iso,
            })
        except Exception as e:
            out.append({'symbol': sym, 'vwap': None, 'error': str(e), 'as_of': now_iso})
    return Response(out, status=status.HTTP_200_OK)

@api_view(['GET'])
def vwap_rolling(request: HttpRequest):
    """GET /api/vwap/rolling?symbols=ES,YM&minutes=30

    Returns rolling VWAP for each symbol over the last `minutes` window.
    If a precomputed Redis payload exists (written by IntradayMarketSupervisor)
    it is used; otherwise falls back to on-demand calculation.
    """
    symbols_param = request.GET.get('symbols') or ''
    minutes_param = request.GET.get('minutes') or '30'
    try:
        window_minutes = int(minutes_param)
    except Exception:
        window_minutes = 30
    symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
    out = []
    now_iso = now().isoformat()
    # Try precomputed hash
    redis_key = f"rolling_vwap:{window_minutes}"
    cached = live_data_redis.client.get(redis_key)
    cached_payload = None
    if cached:
        try:
            cached_payload = json.loads(cached)
        except Exception:
            cached_payload = None
    for sym in symbols:
        val = None
        if cached_payload and cached_payload.get('values'):
            val_str = cached_payload['values'].get(sym)
            val = Decimal(val_str) if val_str is not None else None
        if val is None:
            # Fallback compute
            try:
                val = vwap_service.calculate_rolling_vwap(sym, window_minutes)
            except Exception as e:
                out.append({'symbol': sym, 'vwap': None, 'error': str(e), 'window_minutes': window_minutes, 'as_of': now_iso})
                continue
        out.append({'symbol': sym, 'vwap': f"{val}" if val is not None else None, 'window_minutes': window_minutes, 'as_of': now_iso})
    return Response(out, status=status.HTTP_200_OK)

# API Overview
@api_view(['GET'])
def api_overview(request):
    """
    API Overview endpoint that provides information about available endpoints
    """
    api_urls = {
        'Overview': '/api/',
        'Statistics': '/api/stats/',
        'Quotes Snapshot': '/api/quotes?symbols=ES,YM',
        'Quotes Stream (SSE)': '/api/quotes/stream',
        'WorldClock': '/api/worldclock/',
        'Admin': '/admin/',
    }
    return Response(api_urls)

# Statistics endpoint
@api_view(['GET'])
def api_statistics(request):
    """
    Get statistics about the Thor application
    """
    # Return zeros/None for removed domains (backward compatible shape)
    stats = {
        'total_heroes': 0,
        'total_quests': 0,
        'completed_quests': 0,
        'total_artifacts': 0,
        'most_powerful_hero': None,
        'latest_quest': None,
    }
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
def quotes_snapshot(request: HttpRequest):
    """
    GET /api/quotes?symbols=ES,YM
    Returns latest snapshot for requested symbols from Redis latest-hash keys.
    If no symbols are provided, returns an empty list.
    """
    symbols_param = request.GET.get('symbols') or ''
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return Response([], status=status.HTTP_200_OK)

    r = get_redis()
    out = []
    for sym in symbols:
        data = r.hgetall(latest_key(sym))
        if data:
            # ensure types for common fields when possible
            for num in ('last', 'bid', 'ask'):
                if num in data and data[num] not in (None, ''):
                    try:
                        data[num] = float(data[num])
                    except Exception:
                        pass
            for num in ('lastSize', 'bidSize', 'askSize'):
                if num in data and data[num] not in (None, ''):
                    try:
                        data[num] = int(float(data[num]))
                    except Exception:
                        pass
            data['symbol'] = sym
            out.append(data)
    return Response(out, status=status.HTTP_200_OK)


def _sse_format(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, separators=(',', ':'))
    return f"event: {event}\n" f"data: {payload}\n\n"


@api_view(['GET'])
def quotes_stream(request: HttpRequest):
    """
    GET /api/quotes/stream
    Server-Sent Events stream reading from unified Redis Stream.
    Emits 'quote' events and periodic 'ping' heartbeats.
    """
    r = get_redis()
    stream_key = unified_stream_key()

    # Start at the end by default; use ?from=0-0 to replay
    from_id = request.GET.get('from', '$')
    heartbeat_interval = 10

    def event_generator():
        last_heartbeat = time.time()
        next_id = from_id
        # Initial hello
        yield _sse_format('hello', {'ts': now().isoformat()})
        while True:
            try:
                resp = r.xread({stream_key: next_id}, block=5000, count=100)
                if resp:
                    # resp: [(stream, [(id, {fields})...])]
                    for _, entries in resp:
                        for entry_id, fields in entries:
                            next_id = entry_id
                            # Try to coerce numbers for common fields
                            for k in ('last', 'bid', 'ask'):
                                if k in fields:
                                    try:
                                        fields[k] = float(fields[k])
                                    except Exception:
                                        pass
                            yield _sse_format('quote', {**fields, 'id': entry_id})
                # heartbeat
                if time.time() - last_heartbeat >= heartbeat_interval:
                    last_heartbeat = time.time()
                    yield _sse_format('ping', {'ts': now().isoformat()})
            except GeneratorExit:
                break
            except Exception as e:
                yield _sse_format('error', {'message': str(e)})
                time.sleep(1.0)

    resp = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'  # nginx friendly if used later
    return resp


@api_view(['GET'])
# In dev we allow anonymous reads for the summary so the frontend can render without auth wiring.
# When auth is finalized, switch back to IsAuthenticated only.
@permission_classes([])
def account_statement_summary(request: HttpRequest):
    """
    GET /api/account-statement/summary?account_type=paper|real
    Returns the current summary for the user's selected account.
    If no account is found, returns empty strings for fields.
    """
    account_type = (request.GET.get('account_type') or 'paper').lower()

    def fmt(val: Decimal | None) -> str:
        if val is None:
            return ''
        try:
            return f"${Decimal(val):,.2f}"
        except Exception:
            return str(val)

    def pct(val: Decimal | None) -> str:
        if val is None:
            return ''
        try:
            return f"{Decimal(val):.2f}%"
        except Exception:
            return str(val)

    account = None
    is_authed = getattr(request, 'user', None) and request.user.is_authenticated

    if account_type == 'paper':
        if is_authed:
            account = PaperAccount.objects.filter(user=request.user).first()
            # Optionally auto-provision a paper account for authenticated users with none
            # (commented to avoid side effects; enable if desired)
            # if not account:
            #     account = PaperAccount.objects.create(user=request.user)
        if not account:
            account = PaperAccount.objects.first()
    elif account_type == 'real':
        if is_authed:
            account = RealAccount.objects.filter(user=request.user).first()
        if not account:
            account = RealAccount.objects.first()

    if not account:
        # No account available
        return Response({
            'netLiquidatingValue': '',
            'stockBuyingPower': '',
            'optionBuyingPower': '',
            'dayTradingBuyingPower': '',  # map to stock buying power for now if available
            'availableFundsForTrading': '',
            'longStockValue': '',
            'equityPercentage': '',
        }, status=status.HTTP_200_OK)

    # Map model fields to frontend shape
    data = {
        'netLiquidatingValue': fmt(account.net_liquidating_value),
        'stockBuyingPower': fmt(account.stock_buying_power),
        'optionBuyingPower': fmt(account.option_buying_power),
        'dayTradingBuyingPower': fmt(account.stock_buying_power),  # using stock buying power as placeholder
        'availableFundsForTrading': fmt(account.available_funds_for_trading),
        'longStockValue': fmt(account.long_stock_value),
        'equityPercentage': pct(account.equity_percentage),
    }

    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([])  # Dev-only open; switch to [IsAuthenticated] when auth wiring ready
def account_statement_reset_paper(request: HttpRequest):
    """
    POST /api/account-statement/reset-paper
    Resets the authenticated user's paper account back to its starting balance, or
    falls back to the first PaperAccount if unauthenticated (dev convenience).

    Returns the refreshed summary payload (same shape as /summary) after reset.
    """
    is_authed = getattr(request, 'user', None) and request.user.is_authenticated

    if is_authed:
        account = PaperAccount.objects.filter(user=request.user).first()
        if not account:
            return Response({'detail': 'Paper account not found for user.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Dev fallback: operate on first paper account so UI can demo without auth
        account = PaperAccount.objects.first()
        if not account:
            return Response({'detail': 'No paper account available to reset.'}, status=status.HTTP_404_NOT_FOUND)

    # Perform reset on model
    account.reset_account()

    # Helper formatters (duplicate minimal subset to avoid coupling)
    def fmt(val: Decimal | None) -> str:
        if val is None:
            return ''
        try:
            return f"${Decimal(val):,.2f}"
        except Exception:
            return str(val)

    def pct(val: Decimal | None) -> str:
        if val is None:
            return ''
        try:
            return f"{Decimal(val):.2f}%"
        except Exception:
            return str(val)

    data = {
        'netLiquidatingValue': fmt(account.net_liquidating_value),
        'stockBuyingPower': fmt(account.stock_buying_power),
        'optionBuyingPower': fmt(account.option_buying_power),
        'dayTradingBuyingPower': fmt(account.stock_buying_power),
        'availableFundsForTrading': fmt(account.available_funds_for_trading),
        'longStockValue': fmt(account.long_stock_value),
        'equityPercentage': pct(account.equity_percentage),
        'resetCount': account.reset_count,
        'lastReset': account.last_reset_date.isoformat() if account.last_reset_date else None,
    }

    return Response(data, status=status.HTTP_200_OK)

