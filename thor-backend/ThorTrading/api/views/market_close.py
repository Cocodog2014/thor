"""Manual market close capture endpoint."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ThorTrading.services.sessions import capture_market_close


class MarketCloseCaptureView(APIView):
	"""GET /api/future-trading/market-close/capture?country=United%20States[&force=1]

	Workflow:
		1. Determine latest capture_group for the given country.
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

		result = capture_market_close(country, force=force)

		status_map = {
			"ok": status.HTTP_200_OK,
			"already-closed": status.HTTP_200_OK,
			"no-sessions": status.HTTP_404_NOT_FOUND,
			"error": status.HTTP_500_INTERNAL_SERVER_ERROR,
		}
		http_status = status_map.get(result.get("status"), status.HTTP_200_OK)

		return Response(result, status=http_status)


__all__ = ["MarketCloseCaptureView"]
