from rest_framework import filters, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from datetime import date, timedelta, datetime
import os

from ..models import Market, USMarketStatus, MarketDataSnapshot, UserMarketWatchlist
from ..serializers import (
    MarketSerializer, USMarketStatusSerializer,
    MarketDataSnapshotSerializer, UserMarketWatchlistSerializer
)


class MarketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing global markets
    """
    queryset = Market.objects.all()
    serializer_class = MarketSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_active', 'currency', 'is_control_market']
    search_fields = ['country', 'timezone_name']
    ordering_fields = ['country', 'market_open_time', 'created_at']
    ordering = ['country']
    
    def get_queryset(self):
        """Return ONLY control markets in east→west order (earliest open to latest)."""
        control_countries = [
            'Japan',
            'China',
            'India',
            'Germany',
            'United Kingdom',
            'Pre_USA',
            'USA',
            'Canada',
            'Mexico',
        ]

        queryset = Market.objects.filter(country__in=control_countries).extra(
            select={
                'custom_order': """
                CASE 
                    WHEN country = 'Japan' THEN 1
                    WHEN country = 'China' THEN 2
                    WHEN country = 'India' THEN 3
                    WHEN country = 'Germany' THEN 4
                    WHEN country = 'United Kingdom' THEN 5
                    WHEN country = 'Pre_USA' THEN 6
                    WHEN country = 'USA' THEN 7
                    WHEN country = 'Canada' THEN 8
                    WHEN country = 'Mexico' THEN 9
                    ELSE 999
                END
                """
            }
        ).order_by('custom_order')
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def control(self, request):
        """Return only control markets (9)"""
        qs = Market.objects.filter(is_active=True, is_control_market=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active_markets(self, request):
        """Get all active markets that should be tracked"""
        active_markets = Market.objects.filter(is_active=True, status='OPEN')
        serializer = self.get_serializer(active_markets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def live_status(self, request):
        """Get real-time status of all markets"""
        us_market_open = USMarketStatus.is_us_market_open_today()
        
        if not us_market_open:
            return Response({
                'us_market_open': False,
                'message': 'US markets are closed - no data collection active',
                'markets': []
            })
        
        markets = Market.objects.filter(is_active=True)
        market_data = []
        
        for market in markets:
            status = market.get_market_status()
            if status:
                market_data.append(status)
        
        return Response({
            'us_market_open': True,
            'total_markets': len(market_data),
            'markets': market_data
        })


class USMarketStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing US market trading days and holidays
    """
    queryset = USMarketStatus.objects.all()
    serializer_class = USMarketStatusSerializer
    permission_classes = [AllowAny]
    ordering = ['-date']
    
    @action(detail=False, methods=['get'])
    def today_status(self, request):
        """Get today's US market status"""
        today = date.today()
        is_open = USMarketStatus.is_us_market_open_today()
        
        try:
            status_obj = USMarketStatus.objects.get(date=today)
            serializer = self.get_serializer(status_obj)
            return Response({
                'is_open': is_open,
                'status': serializer.data
            })
        except USMarketStatus.DoesNotExist:
            return Response({
                'is_open': is_open,
                'status': {
                    'date': today,
                    'is_trading_day': is_open,
                    'holiday_name': '' if is_open else 'Weekend',
                    'created_at': None
                }
            })
    
    @action(detail=False, methods=['get'])
    def upcoming_holidays(self, request):
        """Get upcoming US market holidays"""
        today = date.today()
        upcoming = USMarketStatus.objects.filter(
            date__gte=today,
            is_trading_day=False
        ).order_by('date')[:10]
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)


class MarketDataSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing market data snapshots
    """
    queryset = MarketDataSnapshot.objects.all()
    serializer_class = MarketDataSnapshotSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['market', 'market_status', 'dst_active']
    ordering_fields = ['collected_at', 'market_time']
    ordering = ['-collected_at']
    
    @action(detail=False, methods=['get'])
    def latest_snapshots(self, request):
        """Get latest snapshot for each market"""
        latest_snapshots = []
        markets = Market.objects.filter(is_active=True)
        
        for market in markets:
            latest = MarketDataSnapshot.objects.filter(market=market).first()
            if latest:
                latest_snapshots.append(latest)
        
        serializer = self.get_serializer(latest_snapshots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def market_history(self, request):
        """Get recent history for a specific market"""
        market_id = request.query_params.get('market_id')
        hours = int(request.query_params.get('hours', 24))
        
        if not market_id:
            return Response({'error': 'market_id parameter required'}, status=400)
        
        since = datetime.now() - timedelta(hours=hours)
        
        snapshots = MarketDataSnapshot.objects.filter(
            market_id=market_id,
            collected_at__gte=since
        ).order_by('-collected_at')
        
        serializer = self.get_serializer(snapshots, many=True)
        return Response(serializer.data)


class UserMarketWatchlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user's market watchlist
    """
    serializer_class = UserMarketWatchlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserMarketWatchlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder user's watchlist"""
        watchlist_orders = request.data.get('watchlist_orders', [])
        
        for item in watchlist_orders:
            try:
                watchlist_item = UserMarketWatchlist.objects.get(
                    id=item['id'],
                    user=request.user
                )
                watchlist_item.order = item['order']
                watchlist_item.save()
            except UserMarketWatchlist.DoesNotExist:
                continue
        
        return Response({'status': 'success'})


@api_view(['GET'])
@permission_classes([AllowAny])
def worldclock_stats(request):
    """
    Get WorldClock application statistics
    """
    us_market_open = USMarketStatus.is_us_market_open_today()
    
    stats = {
        'us_market_open': us_market_open,
        'total_markets': Market.objects.filter(is_active=True).count(),
        'active_markets': Market.objects.filter(is_active=True, status='OPEN').count(),
        'total_snapshots': MarketDataSnapshot.objects.count(),
        'total_users_with_watchlists': UserMarketWatchlist.objects.values('user').distinct().count(),
    }
    
    last_24h = datetime.now() - timedelta(hours=24)
    stats['recent_snapshots'] = MarketDataSnapshot.objects.filter(
        collected_at__gte=last_24h
    ).count()
    
    if us_market_open:
        open_markets = []
        for market in Market.objects.filter(is_active=True, status='OPEN'):
            if market.is_market_open_now():
                open_markets.append(market.country)
        stats['currently_trading'] = open_markets
    else:
        stats['currently_trading'] = []
    
    return Response(stats)


@api_view(['GET'])
def api_test_page(request):
    """
    Serve the API test page for development/debugging
    """
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_file_path = os.path.join(current_dir, 'api_test.html')
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HttpResponse(html_content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(
            "<h1>Error: api_test.html not found</h1>"
            "<p>Make sure api_test.html is in the project root directory</p>",
            content_type='text/html'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_market_times(request):
    """
    Debug endpoint to check current market times and ordering
    """
    all_markets = Market.objects.all()
    active_markets = Market.objects.filter(is_active=True)
    
    markets = Market.objects.filter(is_active=True).extra(
        select={
            'custom_order': """
            CASE 
                WHEN country = 'Japan' THEN 1
                WHEN country = 'China' THEN 2
                WHEN country = 'India' THEN 3
                WHEN country = 'Germany' THEN 4
                WHEN country = 'United Kingdom' THEN 5
                WHEN country = 'Pre_USA' THEN 6
                WHEN country = 'USA' THEN 7
                WHEN country = 'Canada' THEN 8
                WHEN country = 'Mexico' THEN 9
                ELSE 999
            END
            """
        }
    ).order_by('custom_order')
    
    debug_info = {
        'total_markets_in_db': all_markets.count(),
        'active_markets_count': active_markets.count(),
        'ordered_markets_count': markets.count(),
        'current_time': datetime.now().isoformat(),
        'all_countries': [m.country for m in all_markets],
        'active_countries': [m.country for m in active_markets],
        'markets': []
    }
    
    for market in markets:
        current_time_info = market.get_current_market_time()
        debug_info['markets'].append({
            'position': len(debug_info['markets']) + 1,
            'country': market.country,
            'display_name': market.get_display_name(),
            'sort_order': market.get_sort_order(),
            'timezone': market.timezone_name,
            'market_hours': f"{market.market_open_time} - {market.market_close_time}",
            'current_time': current_time_info,
            'is_active': market.is_active,
            'status': market.status
        })
    
    return Response(debug_info)


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def sync_markets(request):
    """
    Sync markets for development only (kept for compatibility)
    """
    return Response({'detail': 'Deprecated: use control markets config instead.'})
