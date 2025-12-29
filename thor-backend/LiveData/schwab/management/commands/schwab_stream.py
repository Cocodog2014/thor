# schwab_stream.py  (management command)

from __future__ import annotations

import asyncio
import logging
import time
from copy import deepcopy
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from asgiref.sync import sync_to_async

from LiveData.schwab.models import BrokerConnection, SchwabSubscription
from LiveData.schwab.client.streaming import SchwabStreamingProducer
from LiveData.schwab.client.tokens import ensure_valid_access_token


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

    def _load_subscriptions(self, user_id: int) -> tuple[list[str], list[str]]:
        """Load enabled Schwab subscriptions for the user, grouped by asset type.

        Returns: (equities_and_indexes, futures)
        """
        subs = SchwabSubscription.objects.filter(user_id=user_id, enabled=True).values("symbol", "asset_type")

        equities: set[str] = set()
        futures: set[str] = set()

        for sub in subs:
            sym = (sub.get("symbol") or "").lstrip("/").upper()
            if not sym:
                continue

            asset = (sub.get("asset_type") or "").upper()
            if asset in {SchwabSubscription.ASSET_EQUITY, SchwabSubscription.ASSET_INDEX}:
                equities.add(sym)
            elif asset == SchwabSubscription.ASSET_FUTURE:
                futures.add(sym)
            else:
                logger.warning("Ignoring Schwab subscription with unknown asset_type=%s symbol=%s", asset, sym)

        return sorted(equities), sorted(futures)

    def handle(self, *args, **options):
        try:
            from schwab import auth as schwab_auth  # type: ignore
            from schwab.streaming import StreamClient  # type: ignore
        except Exception as exc:
            raise CommandError("schwab-py is not installed. Install with `pip install schwab-py`") from exc

        user_id: int = options["user_id"]
        equities: List[str] = _parse_csv(options.get("equities"))
        futures: List[str] = _parse_csv(options.get("futures"))

        loaded_from_subs = False
        if not equities and not futures:
            equities, futures = self._load_subscriptions(user_id)
            loaded_from_subs = True
            if not equities and not futures:
                raise CommandError("No Schwab subscriptions found for this user; pass --equities/--futures or create subscriptions")

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

        api_key = getattr(settings, "SCHWAB_CLIENT_ID", None) or getattr(settings, "SCHWAB_API_KEY", None)
        app_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)
        account_id = connection.broker_account_id or None

        if not api_key or not app_secret:
            raise CommandError("SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET must be set in settings/.env")
        if not account_id:
            # Auto-resolve broker_account_id (hashValue) from Schwab if missing
            from LiveData.schwab.client.trader import SchwabTraderAPI

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

        # Token cache kept in-memory so schwab-py sync callbacks avoid ORM in async loop
        token_state = {
            "creation_timestamp": int(connection.updated_at.timestamp()) if getattr(connection, "updated_at", None) else int(time.time()),
            "token": {
                "access_token": connection.access_token,
                "refresh_token": connection.refresh_token,
                "expires_at": int(connection.access_expires_at or 0),
                "token_type": "Bearer",
            },
        }

        async def _persist_tokens(payload: dict) -> None:
            # Run DB writes off the event loop thread
            await refresh_from_db_async(connection)
            connection.access_token = payload.get("access_token") or connection.access_token
            connection.refresh_token = payload.get("refresh_token") or connection.refresh_token
            if payload.get("expires_at") is not None:
                connection.access_expires_at = int(payload.get("expires_at") or 0)
            await sync_to_async(connection.save, thread_sensitive=True)(
                update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"],
            )

        # Token functions (schwab-py advanced auth helper). Keep them sync, but make
        # them rely on in-memory state and dispatch persistence to background tasks
        def _read_token():
            return deepcopy(token_state)

        def _write_token(token_obj):
            payload = token_obj.get("token") if isinstance(token_obj, dict) and "token" in token_obj else token_obj
            if not isinstance(payload, dict):
                payload = {}

            token_state["token"].update({
                "access_token": payload.get("access_token") or token_state["token"].get("access_token"),
                "refresh_token": payload.get("refresh_token") or token_state["token"].get("refresh_token"),
                "expires_at": int(payload.get("expires_at") or token_state["token"].get("expires_at") or 0),
                "token_type": "Bearer",
            })
            token_state["creation_timestamp"] = int(time.time())

            loop = asyncio.get_running_loop()
            loop.create_task(_persist_tokens(token_state["token"].copy()))

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

                    # Keep in-memory token cache aligned with the refreshed connection
                    token_state["token"] = {
                        "access_token": conn.access_token,
                        "refresh_token": conn.refresh_token,
                        "expires_at": int(conn.access_expires_at or 0),
                        "token_type": "Bearer",
                    }
                    token_state["creation_timestamp"] = int(
                        conn.updated_at.timestamp()
                    ) if getattr(conn, "updated_at", None) else int(time.time())

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

        source_label = "subscriptions" if loaded_from_subs else "cli"
        self.stdout.write(self.style.SUCCESS(
            f"Starting Schwab stream user_id={user_id} equities={equities or '-'} futures={futures or '-'} source={source_label}"
        ))
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))

