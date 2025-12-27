"""
Run Schwab streaming and forward ticks to Redis + WebSocket.

Usage:
    python manage.py schwab_stream --user-id 1 --equities AAPL,MSFT --futures /ES,/NQ

Requirements:
    - schwab-py installed and configured (client_id/secret in settings)
    - At least one BrokerConnection for the user (broker="SCHWAB")

Notes:
    - This command is intentionally manual (not started at import time).
    - It refreshes the OAuth token if needed and then runs until stopped.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError

from LiveData.schwab.models import BrokerConnection
from LiveData.schwab.streaming import SchwabStreamingProducer
from LiveData.schwab.tokens import ensure_valid_access_token

logger = logging.getLogger(__name__)


def _parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Command(BaseCommand):
    help = "Start Schwab streaming and publish ticks to Redis/WebSocket"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help="Thor user id that owns the Schwab connection",
        )
        parser.add_argument(
            "--equities",
            type=str,
            default="",
            help="Comma-separated equity symbols (e.g. AAPL,MSFT)",
        )
        parser.add_argument(
            "--futures",
            type=str,
            default="",
            help="Comma-separated futures symbols (e.g. /ES,/NQ)",
        )

    def handle(self, *args, **options):
        try:
            from schwab import auth as schwab_auth  # type: ignore
            from schwab import streamer as schwab_streamer  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency check
            raise CommandError(
                "schwab-py is not installed. Install with `pip install schwab-py`"
            ) from exc

        user_id: int = options["user_id"]
        equities: List[str] = _parse_csv(options.get("equities"))
        futures: List[str] = _parse_csv(options.get("futures"))

        try:
            connection = (
                BrokerConnection.objects.select_related("user")
                .filter(user_id=user_id, broker=BrokerConnection.BROKER_SCHWAB)
                .first()
            )
        except Exception as exc:
            raise CommandError(f"Failed to load Schwab connection for user_id={user_id}: {exc}") from exc

        if not connection:
            raise CommandError(f"No Schwab BrokerConnection found for user_id={user_id}")

        # Ensure token freshness
        connection = ensure_valid_access_token(connection)

        # Build Schwab client + streamer via schwab-py
        try:
            client = schwab_auth.client_from_access_token(
                connection.access_token,
                connection.refresh_token,
                int(connection.access_expires_at or 0),
            )
            streamer = schwab_streamer.Streamer(client)
        except Exception as exc:
            raise CommandError(f"Failed to initialize Schwab streamer: {exc}") from exc

        producer = SchwabStreamingProducer()

        async def _run():
            await producer.run(streamer, equities=equities, futures=futures)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting Schwab stream for user_id={user_id} equities={equities or '-'} futures={futures or '-'}"
            )
        )
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:  # pragma: no cover - runtime signal
            self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))
        except Exception as exc:
            raise CommandError(f"Schwab stream failed: {exc}") from exc
