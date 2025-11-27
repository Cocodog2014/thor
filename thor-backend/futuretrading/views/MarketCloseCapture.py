"""Manual Market Close Capture View

Provides an API endpoint to finalize intraday metrics for a market
in case the automatic IntradayMarketSupervisor hook needs a manual
override or re-run. Idempotent unless force=1 passed.
"""
import logging
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from FutureTrading.models.MarketSession import MarketSession
from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.market_metrics import (
    MarketCloseMetric,
    MarketRangeMetric,
)

logger = logging.getLogger(__name__)


class MarketCloseCaptureView(APIView):
    """GET /api/future-trading/market-close/capture?country=United%20States[&force=1]

    Workflow:
      1. Determine latest session_number for the given country.
      2. If close metrics already populated and force not set → skip.
      3. Fetch enriched quotes (single snapshot) for price reference.
      4. Run MarketCloseMetric then MarketRangeMetric.
      5. Return summary JSON.
    """

    def get(self, request):
        country = request.GET.get("country")
        force = request.GET.get("force") == "1"
        if not country:
            return Response({"error": "Missing 'country' query parameter"}, status=status.HTTP_400_BAD_REQUEST)

        latest_session = (
            MarketSession.objects.filter(country=country).aggregate(Max("session_number")).get("session_number__max")
        )
        if latest_session is None:
            return Response({"error": f"No sessions found for country '{country}'"}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency check: if any row has market_close set, assume closed
        already_closed = MarketSession.objects.filter(
            country=country,
            session_number=latest_session,
            market_close__isnull=False,
        ).exists()
        if already_closed and not force:
            return Response(
                {
                    "country": country,
                    "session_number": latest_session,
                    "status": "already-closed",
                    "message": "Close metrics already populated; use force=1 to recompute.",
                },
                status=status.HTTP_200_OK,
            )

        try:
            enriched, _ = get_enriched_quotes_with_composite()
        except Exception as e:
            logger.exception("Failed fetching enriched quotes for close capture %s", country)
            return Response({"error": f"Quote fetch failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            close_updated = MarketCloseMetric.update_for_country_on_close(country, enriched)
        except Exception as e:
            logger.exception("MarketCloseMetric failed for %s", country)
            return Response({"error": f"MarketCloseMetric error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            range_updated = MarketRangeMetric.update_for_country_on_close(country)
        except Exception as e:
            logger.exception("MarketRangeMetric failed for %s", country)
            return Response({"error": f"MarketRangeMetric error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "country": country,
                "session_number": latest_session,
                "status": "ok",
                "force": force,
                "close_rows_updated": close_updated,
                "range_rows_updated": range_updated,
            },
            status=status.HTTP_200_OK,
        )

__all__ = ["MarketCloseCaptureView"]
