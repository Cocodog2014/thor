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

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.serializers.MarketSession import (
    MarketSessionListSerializer,
    MarketSessionDetailSerializer,
    MarketOpenSessionListSerializer,  # backwards compatibility
    MarketOpenSessionDetailSerializer  # backwards compatibility
)
from ThorTrading.constants import CONTROL_COUNTRIES


class MarketSessionListView(APIView):
    """
    GET /api/futures/market-opens/
    
    List all market open sessions with optional filters:
    - country: Filter by market region (Japan, China, Europe, USA, etc.)
    - status: Filter by outcome (WORKED, DIDNT_WORK, NEUTRAL, PENDING)
    - date: Filter by date (YYYY-MM-DD)
    """
    
    def get(self, request):
        queryset = MarketSession.objects.all()
        
        # Apply filters
        country = request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__iexact=country)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(wndw=status_filter.upper())
        
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
        
        serializer = MarketSessionListSerializer(queryset, many=True)
        return Response(serializer.data)


class MarketSessionDetailView(APIView):
    """
    GET /api/futures/market-opens/{id}/
    
    Get detailed view of a single market open session including all futures data.
    """
    
    def get(self, request, pk):
        try:
            session = MarketSession.objects.get(pk=pk)
            serializer = MarketSessionDetailSerializer(session)
            return Response(serializer.data)
        except MarketSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TodayMarketSessionsView(APIView):
    """
    GET /api/futures/market-opens/today/
    
    Get all market open sessions captured today.
    """
    
    def get(self, request):
        today = timezone.now()
        sessions = MarketSession.objects.filter(
            year=today.year,
            month=today.month,
            date=today.day
        )
        serializer = MarketSessionDetailSerializer(sessions, many=True)
        return Response(serializer.data)


class PendingMarketSessionsView(APIView):
    """
    GET /api/futures/market-opens/pending/
    
    Get all sessions that are still pending (outcome not determined).
    """
    
    def get(self, request):
        sessions = MarketSession.objects.filter(wndw='PENDING')
        serializer = MarketSessionDetailSerializer(sessions, many=True)
        return Response(serializer.data)


class MarketSessionStatsView(APIView):
    """
    GET /api/futures/market-opens/stats/
    
    Get aggregate statistics for market open sessions:
    - Total sessions captured
    - Win rate (WORKED vs DIDNT_WORK)
    - Breakdown by market
    - Recent performance
    """
    
    def get(self, request):
        total_sessions = MarketSession.objects.count()
        
        # Overall stats
        worked = MarketSession.objects.filter(wndw='WORKED').count()
        didnt_work = MarketSession.objects.filter(wndw='DIDNT_WORK').count()
        pending = MarketSession.objects.filter(wndw='PENDING').count()
        neutral = MarketSession.objects.filter(wndw='NEUTRAL').count()
        
        # Calculate win rate (exclude pending and neutral)
        graded_sessions = worked + didnt_work
        win_rate = (worked / graded_sessions * 100) if graded_sessions > 0 else 0
        
        # Stats by market
        market_stats = MarketSession.objects.values('country').annotate(
            total=Count('id'),
            worked=Count('id', filter=Q(wndw='WORKED')),
            didnt_work=Count('id', filter=Q(wndw='DIDNT_WORK')),
            pending=Count('id', filter=Q(wndw='PENDING'))
        ).order_by('-total')
        
        # Recent performance (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_sessions = MarketSession.objects.filter(
            captured_at__gte=seven_days_ago
        )
        recent_worked = recent_sessions.filter(wndw='WORKED').count()
        recent_didnt_work = recent_sessions.filter(wndw='DIDNT_WORK').count()
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


class LatestPerMarketSessionsView(APIView):
    """
    GET /api/futures/market-opens/latest/

    Returns the latest captured session per control market (today if present,
    otherwise the most recent prior session). Useful for UI that should always
    show something for each market.
    """

    CONTROL_COUNTRIES = CONTROL_COUNTRIES

    def get(self, request):
        full_sessions = []
        for country in self.CONTROL_COUNTRIES:
            latest = (MarketSession.objects
                      .filter(country=country)
                      .order_by('-captured_at')
                      .first())
            if not latest:
                continue

            session_rows = MarketSession.objects.filter(
                country=country,
                year=latest.year,
                month=latest.month,
                date=latest.date,
                session_number=latest.session_number,
            ).order_by('future')
            full_sessions.extend(session_rows)

        serializer = MarketSessionDetailSerializer(full_sessions, many=True)
        return Response(serializer.data)


__all__ = [
    'MarketSessionListView',
    'MarketSessionDetailView',
    'TodayMarketSessionsView',
    'PendingMarketSessionsView',
    'MarketSessionStatsView',
    'LatestPerMarketSessionsView',
    # Backwards compatibility exports
    'MarketOpenSessionListView',
    'MarketOpenSessionDetailView',
    'TodayMarketOpensView',
    'PendingMarketOpensView',
    'MarketOpenStatsView',
    'LatestPerMarketOpensView',
]

# Backwards compatibility class aliases
MarketOpenSessionListView = MarketSessionListView
MarketOpenSessionDetailView = MarketSessionDetailView
TodayMarketOpensView = TodayMarketSessionsView
PendingMarketOpensView = PendingMarketSessionsView
MarketOpenStatsView = MarketSessionStatsView
LatestPerMarketOpensView = LatestPerMarketSessionsView

