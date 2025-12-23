"""Market open session API views."""

from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ThorTrading.constants import CONTROL_COUNTRIES
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.serializers.MarketSession import (
	MarketOpenSessionDetailSerializer,
	MarketOpenSessionListSerializer,
	MarketSessionDetailSerializer,
	MarketSessionListSerializer,
)


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

		country = request.query_params.get("country")
		if country:
			queryset = queryset.filter(country__iexact=country)

		status_filter = request.query_params.get("status")
		if status_filter:
			queryset = queryset.filter(wndw=status_filter.upper())

		date_filter = request.query_params.get("date")
		if date_filter:
			try:
				date_obj = datetime.strptime(date_filter, "%Y-%m-%d")
				queryset = queryset.filter(
					year=date_obj.year,
					month=date_obj.month,
					date=date_obj.day,
				)
			except ValueError:
				return Response(
					{"error": "Invalid date format. Use YYYY-MM-DD"},
					status=status.HTTP_400_BAD_REQUEST,
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
			return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)


class TodayMarketSessionsView(APIView):
	"""
	GET /api/futures/market-opens/today/

	Get all market open sessions captured today (capture_group-based).
	"""

	def get(self, request):
		today = timezone.now().date()

		capture_groups = (
			MarketSession.objects.filter(captured_at__date=today, capture_group__isnull=False)
			.values_list("capture_group", flat=True)
			.distinct()
		)

		if capture_groups:
			sessions = MarketSession.objects.filter(capture_group__in=capture_groups)
		else:
			sessions = MarketSession.objects.filter(
				year=today.year,
				month=today.month,
				date=today.day,
			)

		serializer = MarketSessionDetailSerializer(sessions, many=True)
		return Response(serializer.data)


class PendingMarketSessionsView(APIView):
	"""
	GET /api/futures/market-opens/pending/

	Get all sessions that are still pending (outcome not determined).
	"""

	def get(self, request):
		sessions = MarketSession.objects.filter(wndw="PENDING")
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
		total_sessions = MarketSession.objects.exclude(capture_group__isnull=True).count()

		base_qs = MarketSession.objects.exclude(capture_group__isnull=True)
		worked = base_qs.filter(wndw="WORKED").count()
		didnt_work = base_qs.filter(wndw="DIDNT_WORK").count()
		pending = base_qs.filter(wndw="PENDING").count()
		neutral = base_qs.filter(wndw="NEUTRAL").count()

		graded_sessions = worked + didnt_work
		win_rate = (worked / graded_sessions * 100) if graded_sessions > 0 else 0

		market_stats = (
			MarketSession.objects.exclude(capture_group__isnull=True)
			.values("country", "capture_group")
			.annotate(
				total=Count("id"),
				worked=Count("id", filter=Q(wndw="WORKED")),
				didnt_work=Count("id", filter=Q(wndw="DIDNT_WORK")),
				pending=Count("id", filter=Q(wndw="PENDING")),
			)
		)

		country_rollup = {}
		for row in market_stats:
			country = row["country"]
			agg = country_rollup.setdefault(country, {"total": 0, "worked": 0, "didnt_work": 0, "pending": 0})
			agg["total"] += row["total"]
			agg["worked"] += row["worked"]
			agg["didnt_work"] += row["didnt_work"]
			agg["pending"] += row["pending"]

		ordered_stats = [
			{"country": country, **vals}
			for country, vals in sorted(country_rollup.items(), key=lambda kv: kv[1]["total"], reverse=True)
		]

		seven_days_ago = timezone.now() - timedelta(days=7)
		recent_sessions = MarketSession.objects.filter(captured_at__gte=seven_days_ago)
		recent_worked = recent_sessions.filter(wndw="WORKED").count()
		recent_didnt_work = recent_sessions.filter(wndw="DIDNT_WORK").count()
		recent_graded = recent_worked + recent_didnt_work
		recent_win_rate = (recent_worked / recent_graded * 100) if recent_graded > 0 else 0

		return Response(
			{
				"overall": {
					"total_sessions": total_sessions,
					"worked": worked,
					"didnt_work": didnt_work,
					"pending": pending,
					"neutral": neutral,
					"win_rate": round(win_rate, 2),
				},
				"by_market": ordered_stats,
				"recent_7_days": {
					"total": recent_sessions.count(),
					"worked": recent_worked,
					"didnt_work": recent_didnt_work,
					"win_rate": round(recent_win_rate, 2),
				},
			}
		)


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
			latest = (
				MarketSession.objects.filter(country=country, capture_group__isnull=False)
				.order_by("-capture_group", "-captured_at")
				.first()
			)
			if not latest:
				continue

			session_rows = MarketSession.objects.filter(
				country=country,
				capture_group=latest.capture_group,
			).order_by("future")
			full_sessions.extend(session_rows)

		serializer = MarketSessionDetailSerializer(full_sessions, many=True)
		return Response(serializer.data)


__all__ = [
	"MarketSessionListView",
	"MarketSessionDetailView",
	"TodayMarketSessionsView",
	"PendingMarketSessionsView",
	"MarketSessionStatsView",
	"LatestPerMarketSessionsView",
	"MarketOpenSessionListView",
	"MarketOpenSessionDetailView",
	"TodayMarketOpensView",
	"PendingMarketOpensView",
	"MarketOpenStatsView",
	"LatestPerMarketOpensView",
]

MarketOpenSessionListView = MarketSessionListView
MarketOpenSessionDetailView = MarketSessionDetailView
TodayMarketOpensView = TodayMarketSessionsView
PendingMarketOpensView = PendingMarketSessionsView
MarketOpenStatsView = MarketSessionStatsView
LatestPerMarketOpensView = LatestPerMarketSessionsView
