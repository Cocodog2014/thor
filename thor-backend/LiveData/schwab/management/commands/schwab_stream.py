# schwab_stream.py  (management command)

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from asgiref.sync import async_to_sync, sync_to_async

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

        # Preflight refresh so we do not start streaming with an about-to-expire token
        connection = ensure_valid_access_token(connection, buffer_seconds=120)

        refresh_from_db_async = sync_to_async(lambda obj: obj.refresh_from_db(), thread_sensitive=True)
        ensure_token_async = sync_to_async(ensure_valid_access_token, thread_sensitive=True)

        def _db_refresh(obj):
            obj.refresh_from_db()

        def _db_save(obj, **kwargs):
            obj.save(**kwargs)

        refresh_db_sync = async_to_sync(sync_to_async(_db_refresh, thread_sensitive=True))
        save_sync = async_to_sync(sync_to_async(_db_save, thread_sensitive=True))

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
            # schwab-py expects sync callbacks; wrap DB work safely
            refresh_db_sync(connection)
            token = {
                "access_token": connection.access_token,
                "refresh_token": connection.refresh_token,
                "expires_at": int(connection.access_expires_at or 0),
                "token_type": "Bearer",
            }
            creation_ts = int(connection.updated_at.timestamp()) if getattr(connection, "updated_at", None) else int(time.time())
            return {"creation_timestamp": creation_ts, "token": token}

        def _write_token(token_obj):
            # schwab-py expects sync callbacks; wrap DB work safely
            refresh_db_sync(connection)
            payload = token_obj.get("token") if isinstance(token_obj, dict) and "token" in token_obj else token_obj
            if not isinstance(payload, dict):
                payload = {}

            connection.access_token = payload.get("access_token") or connection.access_token
            connection.refresh_token = payload.get("refresh_token") or connection.refresh_token

            if payload.get("expires_at") is not None:
                connection.access_expires_at = int(payload.get("expires_at") or 0)

            save_sync(
                connection,
                update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"],
            )

        producer = SchwabStreamingProducer()

        async def _run():
            backoff = 2
            max_backoff = 60

            while True:
                try:
                    # Use a local variable (avoid scope issues) + keep DB ops async-safe
                    conn = connection
                    await refresh_from_db_async(conn)
                    conn = await ensure_token_async(conn, buffer_seconds=120)

                    api_client = schwab_auth.client_from_access_functions(
                        api_key,
                        app_secret,
                        token_read_func=_read_token,
                        token_write_func=_write_token,
                        asyncio=True,
                    )

                    stream_client = StreamClient(api_client, account_id=str(account_id))
                    await stream_client.login()

                    # Reset backoff after a successful connect/login
                    backoff = 2

                    # Handlers must be added BEFORE subscribing (docs warn about dropped messages)
                    if equities:
                        stream_client.add_level_one_equity_handler(producer.process_message)
                        await stream_client.level_one_equity_subs([s.upper() for s in equities])

                    if futures:
                        stream_client.add_level_one_futures_handler(producer.process_message)
                        await stream_client.level_one_futures_subs([s.upper() for s in futures])

                    while True:
                        await stream_client.handle_message()

                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "Schwab stream loop error; reconnecting in %ss: %s", backoff, exc, exc_info=True
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)

        self.stdout.write(self.style.SUCCESS(
            f"Starting Schwab stream user_id={user_id} equities={equities or '-'} futures={futures or '-'}"
        ))
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))

