# schwab_stream.py  (management command)

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
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument("--equities", type=str, default="")
        parser.add_argument("--futures", type=str, default="")

    def handle(self, *args, **options):
        try:
            from schwab import auth as schwab_auth  # type: ignore
            from schwab.streaming import StreamClient  # type: ignore
        except Exception as exc:
            raise CommandError("schwab-py is not installed. Install with `pip install schwab-py`") from exc

        user_id: int = options["user_id"]
        equities: List[str] = _parse_csv(options.get("equities"))
        futures: List[str] = _parse_csv(options.get("futures"))

        connection = (
            BrokerConnection.objects.select_related("user")
            .filter(user_id=user_id, broker=BrokerConnection.BROKER_SCHWAB)
            .first()
        )
        if not connection:
            raise CommandError(f"No Schwab BrokerConnection found for user_id={user_id}")

        # refresh tokens in DB if needed
        connection = ensure_valid_access_token(connection)

        api_key = getattr(settings, "SCHWAB_CLIENT_ID", None) or getattr(settings, "SCHWAB_API_KEY", None)
        app_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)
        account_id = connection.broker_account_id or None

        if not api_key or not app_secret:
            raise CommandError("SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET must be set in settings/.env")
        if not account_id:
            raise CommandError("Schwab connection missing broker_account_id; cannot start stream")

        # Token functions (schwab-py advanced auth helper)
        def _read_token():
            return {
                "access_token": connection.access_token,
                "refresh_token": connection.refresh_token,
                "expires_at": int(connection.access_expires_at or 0),
                "token_type": "Bearer",
            }

        def _write_token(token: dict):
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
            stream_client = StreamClient(api_client, account_id=int(account_id))
        except Exception as exc:
            raise CommandError(f"Failed to initialize Schwab StreamClient: {exc}") from exc

        producer = SchwabStreamingProducer()

        async def _run():
            await stream_client.login()

            # ✅ IMPORTANT: handlers must be added BEFORE subscribing (docs warn about dropped messages)
            if equities:
                stream_client.add_level_one_equity_handler(producer.process_message)
                await stream_client.level_one_equity_subs(equities)

            if futures:
                stream_client.add_level_one_futures_handler(producer.process_message)
                await stream_client.level_one_futures_subs(futures)

            # ✅ handle_message dispatches to handlers internally
            while True:
                await stream_client.handle_message()

        self.stdout.write(self.style.SUCCESS(
            f"Starting Schwab stream user_id={user_id} equities={equities or '-'} futures={futures or '-'}"
        ))
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))

