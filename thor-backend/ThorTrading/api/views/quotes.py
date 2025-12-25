from __future__ import annotations
"""Real-Time Data (RTD) views."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ThorTrading.config.symbols import SYMBOL_NORMALIZE_MAP
from ThorTrading.models import TradingInstrument
from ThorTrading.models.extremes import Rolling52WeekStats
from ThorTrading.services.quotes import get_enriched_quotes_with_composite

logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
	"""
	API view that returns latest market data and signals for all active futures instruments
	with statistical values and weighted total composite score.
	"""

	def get(self, request):
		try:
			rows, total = get_enriched_quotes_with_composite()
			return Response({"rows": rows, "total": total}, status=status.HTTP_200_OK)
		except Exception as exc:  # noqa: BLE001
			logger.error("Error in LatestQuotesView: %s", exc)
			return Response({"error": "Internal server error", "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RibbonQuotesView(APIView):
	"""
	API view that returns live data only for instruments marked with show_in_ribbon=True.
	Returns minimal data optimized for ticker ribbon display.
	"""

	def get(self, request):
		try:
			rows, _ = get_enriched_quotes_with_composite()

			ribbon_instruments = (
				TradingInstrument.objects.filter(is_active=True, show_in_ribbon=True)
				.order_by("sort_order", "symbol")
			)

			ribbon_symbols = set()
			for instr in ribbon_instruments:
				ribbon_symbols.add(instr.symbol)
				if instr.symbol.startswith("/"):
					ribbon_symbols.add(instr.symbol[1:])
				else:
					ribbon_symbols.add(f"/{instr.symbol}")

			ribbon_data = []
			for row in rows:
				symbol = row.get("instrument", {}).get("symbol", "")
				if symbol in ribbon_symbols:
					ribbon_data.append(
						{
							"symbol": symbol,
							"name": row.get("instrument", {}).get("name", ""),
							"price": row.get("price"),
							"last": row.get("last"),
							"change": row.get("change"),
							"change_percent": row.get("change_percent"),
							"signal": row.get("signal"),
						}
					)

			return Response(
				{
					"symbols": ribbon_data,
					"count": len(ribbon_data),
					"last_updated": timezone.now().isoformat(),
				},
				status=status.HTTP_200_OK,
			)

		except Exception as exc:  # noqa: BLE001
			logger.error("Error in RibbonQuotesView: %s", exc)
			return Response({"error": "Internal server error", "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


__all__ = ["LatestQuotesView", "RibbonQuotesView"]
