from __future__ import annotations
"""Manual market open capture endpoint."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ThorTrading.GlobalMarketGate.open_capture import capture_market_open


class MarketOpenCaptureView(APIView):
	"""POST /api/future-trading/market-open/capture

	Request body:
		{
			"country": "United States"
		}

	Workflow:
		1. Load market by country from GlobalMarkets.
		2. Verify market is open and capture is enabled.
		3. Call capture_market_open service to create MarketSession records.
		4. Return summary JSON.
	"""

	def post(self, request):
		from GlobalMarkets.models.market import Market

		country = request.data.get("country")
		if not country:
			return Response(
				{"error": "Missing 'country' in request body"},
				status=status.HTTP_400_BAD_REQUEST
			)

		try:
			market = Market.objects.get(country=country)
		except Market.DoesNotExist:
			return Response(
				{"error": f"Market not found for country: {country}"},
				status=status.HTTP_404_NOT_FOUND
			)

		try:
			result = capture_market_open(market)
			if result:
				return Response(
					{
						"status": "ok",
						"session_number": result.session_number,
						"country": result.country,
					},
					status=status.HTTP_201_CREATED
				)
			else:
				return Response(
					{
						"status": "skipped",
						"message": "Capture was skipped (may be disabled or no data available)"
					},
					status=status.HTTP_200_OK
				)
		except Exception as e:
			return Response(
				{
					"status": "error",
					"error": str(e)
				},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)


__all__ = ["MarketOpenCaptureView"]
