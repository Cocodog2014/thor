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
from typing import List, Optional

from django.conf import settings
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
            from schwab.streaming import StreamClient  # type: ignore
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

        # Ensure token freshness in DB
        connection = ensure_valid_access_token(connection)

        api_key = getattr(settings, "SCHWAB_CLIENT_ID", None) or getattr(settings, "SCHWAB_API_KEY", None)
        app_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)
        callback_url = getattr(settings, "SCHWAB_REDIRECT_URI", None)
        account_id = connection.broker_account_id or None

        if not api_key or not app_secret or not callback_url:
            raise CommandError("SCHWAB_CLIENT_ID/SECRET/REDIRECT_URI must be set in settings/.env")
        if not account_id:
            raise CommandError("Schwab connection is missing broker_account_id; cannot start stream")

        # Wire schwab-py client using access_functions so tokens live in DB
        def _read_token():
            return {
                "access_token": connection.access_token,
                "refresh_token": connection.refresh_token,
                "expires_at": int(connection.access_expires_at or 0),
                "token_type": "Bearer",
            }

        def _write_token(token):
            connection.access_token = token.get("access_token", connection.access_token)
            connection.refresh_token = token.get("refresh_token", connection.refresh_token)
            connection.access_expires_at = int(token.get("expires_at", connection.access_expires_at or 0))
            connection.save(update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"])

        try:
            api_client = schwab_auth.client_from_access_functions(
                api_key,
                app_secret,
                token_read_func=_read_token,
                token_write_func=_write_token,
                asyncio=True,
            )
            streamer = StreamClient(api_client, account_id=str(account_id))
        except Exception as exc:
            raise CommandError(f"Failed to initialize Schwab StreamClient: {exc}") from exc

        producer = SchwabStreamingProducer()

        async def _run():
            await streamer.login()
            # Level one quotes for equities/futures
            if equities:
                await streamer.level_one_equity_subs(equities)
                await streamer.add_level_one_equity_handler(producer.process_message)
            if futures:
                await streamer.level_one_futures_subs(futures)
                await streamer.add_level_one_futures_handler(producer.process_message)
            # Main loop
            while True:
                msg = await streamer.handle_message()
                if msg is not None:
                    producer.process_message(msg)

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
