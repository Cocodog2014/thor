# schwab_stream.py  (management command)

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from LiveData.schwab.models import BrokerConnection
from LiveData.schwab.streaming import SchwabStreamingProducer


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

        api_key = getattr(settings, "SCHWAB_CLIENT_ID", None) or getattr(settings, "SCHWAB_API_KEY", None)
        app_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)
        account_id = connection.broker_account_id or None

        if not api_key or not app_secret:
            raise CommandError("SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET must be set in settings/.env")
        if not account_id:
            # Auto-resolve broker_account_id (hashValue) from Schwab if missing
            from LiveData.schwab.services import SchwabTraderAPI

            try:
                api = SchwabTraderAPI(connection.user)
                accounts = api.fetch_accounts() or []
                acct_hash_map = api.fetch_account_numbers_map()

                if not accounts:
                    raise CommandError("No Schwab accounts returned; cannot resolve broker_account_id")

                sec = (accounts[0] or {}).get("securitiesAccount", {}) or {}
                account_number = sec.get("accountNumber") or (accounts[0] or {}).get("accountNumber")

                if not account_number:
                    raise CommandError("Unable to find Schwab accountNumber to resolve hashValue")

                account_id = acct_hash_map.get(str(account_number))
                if not account_id:
                    account_id = api.resolve_account_hash(str(account_number))

                connection.broker_account_id = str(account_id)
                connection.save(update_fields=["broker_account_id", "updated_at"])

            except Exception as exc:
                raise CommandError(
                    f"Schwab connection missing broker_account_id and auto-resolve failed: {exc}"
                )
        if not account_id:
            raise CommandError("Schwab connection missing broker_account_id; cannot start stream")

        # Token functions (schwab-py advanced auth helper)
        def _read_token():
            # schwab-py 1.5.x expects a metadata wrapper with creation_timestamp
            creation_ts = int(connection.created_at.timestamp()) if getattr(connection, "created_at", None) else 0
            return {
                "creation_timestamp": creation_ts,
                "token": {
                    "access_token": connection.access_token,
                    "refresh_token": connection.refresh_token,
                    "expires_at": int(connection.access_expires_at or 0),
                    "token_type": "Bearer",
                },
            }

        def _write_token(token_obj):
            # token_obj may be wrapped or flat; handle both
            inner = token_obj.get("token") if isinstance(token_obj, dict) else None
            if not isinstance(inner, dict):
                inner = token_obj if isinstance(token_obj, dict) else {}

            connection.access_token = inner.get("access_token", connection.access_token)
            connection.refresh_token = inner.get("refresh_token", connection.refresh_token)

            if "expires_at" in inner:
                connection.access_expires_at = int(inner.get("expires_at") or 0)

            connection.save(update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"])

        try:
            api_client = schwab_auth.client_from_access_functions(
                api_key,
                app_secret,
                token_read_func=_read_token,
                token_write_func=_write_token,
                asyncio=True,
            )
            # Pass as string to preserve any leading zeros or non-numeric chars stored in broker_account_id
            stream_client = StreamClient(api_client, account_id=str(account_id))
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

