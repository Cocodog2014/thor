"""
Market-Open Capture API Views

Provides endpoints to view and analyze market open capture sessions.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

from FutureTrading.models.MarketOpen import MarketOpenSession
from FutureTrading.serializers.MarketOpen import (
    MarketOpenSessionListSerializer,
    MarketOpenSessionDetailSerializer
)


class MarketOpenSessionListView(APIView):
    """
    GET /api/futures/market-opens/
    
    List all market open sessions with optional filters:
    - country: Filter by market region (Japan, China, Europe, USA, etc.)
    - status: Filter by outcome (WORKED, DIDNT_WORK, NEUTRAL, PENDING)
    - date: Filter by date (YYYY-MM-DD)
    """
    
    def get(self, request):
        queryset = MarketOpenSession.objects.all()
        
        # Apply filters
        country = request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__iexact=country)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(fw_nwdw=status_filter.upper())
        
        date_filter = request.query_params.get('date')
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
                queryset = queryset.filter(
                    year=date_obj.year,
                    month=date_obj.month,
                    date=date_obj.day
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = MarketOpenSessionListSerializer(queryset, many=True)
        return Response(serializer.data)


class MarketOpenSessionDetailView(APIView):
    """
    GET /api/futures/market-opens/{id}/
    
    Get detailed view of a single market open session including all futures data.
    """
    
    def get(self, request, pk):
        try:
            session = MarketOpenSession.objects.get(pk=pk)
            serializer = MarketOpenSessionDetailSerializer(session)
            return Response(serializer.data)
        except MarketOpenSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TodayMarketOpensView(APIView):
    """
    GET /api/futures/market-opens/today/
    
    Get all market open sessions captured today.
    """
    
    def get(self, request):
        today = timezone.now()
        sessions = MarketOpenSession.objects.filter(
            year=today.year,
            month=today.month,
            date=today.day
        )
        serializer = MarketOpenSessionDetailSerializer(sessions, many=True)
        return Response(serializer.data)


class PendingMarketOpensView(APIView):
    """
    GET /api/futures/market-opens/pending/
    
    Get all sessions that are still pending (outcome not determined).
    """
    
    def get(self, request):
        sessions = MarketOpenSession.objects.filter(fw_nwdw='PENDING')
        serializer = MarketOpenSessionDetailSerializer(sessions, many=True)
        return Response(serializer.data)


class MarketOpenStatsView(APIView):
    """
    GET /api/futures/market-opens/stats/
    
    Get aggregate statistics for market open sessions:
    - Total sessions captured
    - Win rate (WORKED vs DIDNT_WORK)
    - Breakdown by market
    - Recent performance
    """
    
    def get(self, request):
        total_sessions = MarketOpenSession.objects.count()
        
        # Overall stats
        worked = MarketOpenSession.objects.filter(fw_nwdw='WORKED').count()
        didnt_work = MarketOpenSession.objects.filter(fw_nwdw='DIDNT_WORK').count()
        pending = MarketOpenSession.objects.filter(fw_nwdw='PENDING').count()
        neutral = MarketOpenSession.objects.filter(fw_nwdw='NEUTRAL').count()
        
        # Calculate win rate (exclude pending and neutral)
        graded_sessions = worked + didnt_work
        win_rate = (worked / graded_sessions * 100) if graded_sessions > 0 else 0
        
        # Stats by market
        market_stats = MarketOpenSession.objects.values('country').annotate(
            total=Count('id'),
            worked=Count('id', filter=Q(fw_nwdw='WORKED')),
            didnt_work=Count('id', filter=Q(fw_nwdw='DIDNT_WORK')),
            pending=Count('id', filter=Q(fw_nwdw='PENDING'))
        ).order_by('-total')
        
        # Recent performance (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_sessions = MarketOpenSession.objects.filter(
            captured_at__gte=seven_days_ago
        )
        recent_worked = recent_sessions.filter(fw_nwdw='WORKED').count()
        recent_didnt_work = recent_sessions.filter(fw_nwdw='DIDNT_WORK').count()
        recent_graded = recent_worked + recent_didnt_work
        recent_win_rate = (recent_worked / recent_graded * 100) if recent_graded > 0 else 0
        
        return Response({
            'overall': {
                'total_sessions': total_sessions,
                'worked': worked,
                'didnt_work': didnt_work,
                'pending': pending,
                'neutral': neutral,
                'win_rate': round(win_rate, 2)
            },
            'by_market': list(market_stats),
            'recent_7_days': {
                'total': recent_sessions.count(),
                'worked': recent_worked,
                'didnt_work': recent_didnt_work,
                'win_rate': round(recent_win_rate, 2)
            }
        })


class LatestPerMarketOpensView(APIView):
    """
    GET /api/futures/market-opens/latest/

    Returns the latest captured session per control market (today if present,
    otherwise the most recent prior session). Useful for UI that should always
    show something for each market.
    """

    CONTROL_COUNTRIES = [
        'Japan', 'China', 'India', 'Germany', 'United Kingdom',
        'Pre_USA', 'USA', 'Canada', 'Mexico'
    ]

    def get(self, request):
        sessions = []
        for country in self.CONTROL_COUNTRIES:
            latest = (MarketOpenSession.objects
                      .filter(country=country)
                      .order_by('-captured_at')
                      .first())
            if latest:
                sessions.append(latest)

        # Return detailed serializer
        serializer = MarketOpenSessionDetailSerializer(sessions, many=True)
        return Response(serializer.data)


__all__ = [
    'MarketOpenSessionListView',
    'MarketOpenSessionDetailView',
    'TodayMarketOpensView',
    'PendingMarketOpensView',
    'MarketOpenStatsView',
    'LatestPerMarketOpensView',
]
