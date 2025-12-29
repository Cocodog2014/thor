# schwab_stream.py  (management command)

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import threading
import time
from copy import deepcopy
from typing import List, Optional, Dict, Tuple, Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from LiveData.schwab.models import BrokerConnection, SchwabSubscription
from LiveData.schwab.client.streaming import SchwabStreamingProducer
from LiveData.schwab.client.tokens import ensure_valid_access_token
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


def _parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _group_subscriptions(subs: List[Dict[str, str]]) -> Tuple[List[str], List[str]]:
    """
    Returns (equities_and_indexes, futures)
    Treat INDEX as equity-stream for now (Schwab symbol formats vary, but the feed is typically equity L1).
    """
    equities: List[str] = []
    futures: List[str] = []

    for row in subs:
        sym = (row.get("symbol") or "").strip().upper()
        typ = (row.get("asset_type") or "").strip().upper()
        if not sym:
            continue

        if typ in {"FUTURE", "FUTURES"}:
            futures.append(sym)
        else:
            # EQUITY + INDEX + anything else we want to try on equity L1 feed
            equities.append(sym)

    # de-dupe stable
    def _dedupe(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return _dedupe(equities), _dedupe(futures)


async def _ws_keepalive(sock: Any, *, interval: float = 20.0) -> None:
    """Best-effort websocket keepalive.

    Some streaming servers close idle connections unless the client sends periodic pings.
    websockets' `ping()` typically returns an awaitable that resolves when the pong is received.
    """

    while True:
        try:
            ping_fn = getattr(sock, "ping", None)
            if ping_fn is None:
                return

            pong_waiter = ping_fn()
            if asyncio.iscoroutine(pong_waiter):
                pong_waiter = await pong_waiter
            if pong_waiter is not None:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(pong_waiter, timeout=10)

            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            return


def _control_channel(user_id: int) -> str:
    return f"live_data:schwab:control:{user_id}"


def _start_pubsub_thread(
    user_id: int,
    queue: "asyncio.Queue[dict]",
    loop: asyncio.AbstractEventLoop,
) -> threading.Thread:
    """Runs Redis pubsub.listen() in a background thread (blocking).

    Pushes parsed JSON control messages into the asyncio queue without blocking the event loop.
    """

    channel = _control_channel(user_id)

    def _worker() -> None:
        pubsub = live_data_redis.client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        logger.warning("Schwab control plane subscribed to Redis channel=%s", channel)
        try:
            for msg in pubsub.listen():
                data = msg.get("data")
                if not data:
                    continue
                try:
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode("utf-8", errors="ignore")
                    payload = json.loads(data)
                    if isinstance(payload, dict):
                        loop.call_soon_threadsafe(queue.put_nowait, payload)
                except Exception:
                    continue
        finally:
            with contextlib.suppress(Exception):
                pubsub.close()

    t = threading.Thread(target=_worker, name=f"schwab-control-{user_id}", daemon=True)
    t.start()
    return t


class Command(BaseCommand):
    help = "Start Schwab streaming and publish ticks to Redis/WebSocket (auto-loads user subscriptions by default)"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, required=True)
        # Backward compatible overrides
        parser.add_argument("--equities", type=str, default="")
        parser.add_argument("--futures", type=str, default="")
        # Optional: force-load only specific types from DB (rarely needed)
        parser.add_argument(
            "--types",
            type=str,
            default="",
            help="Optional filter for DB subscriptions: EQUITY,INDEX,FUTURE (comma-separated)",
        )
        parser.add_argument(
            "--exit-after-first",
            action="store_true",
            default=False,
            help="Exit after the first received streaming message (debug/verification)",
        )

    def handle(self, *args, **options):
        try:
            from schwab import auth as schwab_auth  # type: ignore
            from schwab.streaming import StreamClient  # type: ignore
            from websockets.exceptions import ConnectionClosed  # type: ignore
        except Exception as exc:
            raise CommandError("schwab-py is not installed. Install with `pip install schwab-py`") from exc

        user_id: int = options["user_id"]
        exit_after_first: bool = bool(options.get("exit_after_first"))
        echo_ticks: bool = int(options.get("verbosity", 1) or 0) >= 1

        # CLI overrides (still supported)
        equities: List[str] = _parse_csv(options.get("equities"))
        futures: List[str] = _parse_csv(options.get("futures"))

        # If no CLI overrides, load from DB subscriptions
        if not equities and not futures:
            types_filter = set(_parse_csv(options.get("types")))
            qs = SchwabSubscription.objects.filter(user_id=user_id, enabled=True)
            if types_filter:
                qs = qs.filter(asset_type__in=list(types_filter))

            rows = list(qs.values("symbol", "asset_type"))
            equities, futures = _group_subscriptions(rows)

            if not equities and not futures:
                raise CommandError(
                    f"No enabled SchwabSubscription rows found for user_id={user_id}.\n"
                    "Add symbols in Admin → SchwabLiveData → Schwab subscriptions, or run with:\n"
                    "  python manage.py schwab_stream --user-id 1 --equities NVDA,MSFT\n"
                    "  python manage.py schwab_stream --user-id 1 --futures ES,NQ"
                )

        # In-memory desired subscriptions (mutable via Redis control plane)
        desired_equities: set[str] = set([s.upper() for s in equities if s])
        desired_futures: set[str] = set([s.upper() for s in futures if s])

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
            "creation_timestamp": int(connection.updated_at.timestamp())
            if getattr(connection, "updated_at", None)
            else int(time.time()),
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

        def _read_token():
            return deepcopy(token_state)

        def _write_token(token_obj, *args, **kwargs):
            """schwab-py/authlib may pass refresh_token via kwargs; accept *args/**kwargs."""

            payload = token_obj.get("token") if isinstance(token_obj, dict) and "token" in token_obj else token_obj
            if not isinstance(payload, dict):
                payload = {}

            kw_refresh = kwargs.get("refresh_token")
            if kw_refresh and not payload.get("refresh_token"):
                payload["refresh_token"] = kw_refresh

            token_state["token"].update(
                {
                    "access_token": payload.get("access_token") or token_state["token"].get("access_token"),
                    "refresh_token": payload.get("refresh_token") or token_state["token"].get("refresh_token"),
                    "expires_at": int(payload.get("expires_at") or token_state["token"].get("expires_at") or 0),
                    "token_type": payload.get("token_type") or "Bearer",
                }
            )
            token_state["creation_timestamp"] = int(time.time())

            loop = asyncio.get_running_loop()
            loop.create_task(_persist_tokens(token_state["token"].copy()))

        producer = SchwabStreamingProducer()

        def _echo_message(msg: object) -> None:
            """Best-effort terminal echo of all ticks in a message.

            Uses the same normalizer as the Redis publisher so you see exactly
            what the app is ingesting.
            """

            if not echo_ticks:
                return
            if not isinstance(msg, dict):
                return

            ticks = msg.get("content") if isinstance(msg.get("content"), list) else [msg]
            if not ticks:
                return

            now = time.time()
            for tick in ticks:
                if not isinstance(tick, dict):
                    continue
                try:
                    payload = producer._normalize_payload(tick)
                    if not payload:
                        continue
                    age = round(max(0.0, now - float(payload.get("timestamp") or now)), 1)
                    self.stdout.write(
                        f"{payload.get('symbol')} bid={payload.get('bid')} ask={payload.get('ask')} "
                        f"last={payload.get('last')} vol={payload.get('volume')} age_s={age}"
                    )
                except Exception:
                    # Never let terminal output break streaming.
                    continue

        async def _run():
            backoff = 2
            max_backoff = 60

            # Desired sets (mutable via Redis control plane).
            current_equities: set[str] = set(desired_equities)
            current_futures: set[str] = set(desired_futures)

            # Track what we've actually applied to the current stream connection.
            applied_equities: set[str] = set()
            applied_futures: set[str] = set()

            # Per-connection state (reinitialized on reconnect)
            equity_fields: list[Any] = []
            futures_fields: list[Any] = []
            message_handler: Any | None = None
            equity_handler_added: bool = False
            futures_handler_added: bool = False

            async def _apply_equity_subs(stream_client: Any, desired: set[str]) -> None:
                """Apply equity subscription set to the streamer.

                Prefer unsubs if available; otherwise fall back to resubscribing the full desired list.
                """
                nonlocal applied_equities, equity_handler_added

                desired_list = sorted([s.upper() for s in desired if s])
                if not desired_list:
                    unsubs = getattr(stream_client, "level_one_equity_unsubs", None)
                    if callable(unsubs) and applied_equities:
                        await unsubs(sorted(list(applied_equities)))
                    applied_equities = set()
                    return

                if not equity_fields:
                    return

                # Ensure handler is installed exactly once per connection.
                if not equity_handler_added and message_handler is not None:
                    try:
                        stream_client.add_level_one_equity_handler(message_handler)
                        equity_handler_added = True
                    except Exception:
                        pass

                unsubs = getattr(stream_client, "level_one_equity_unsubs", None)
                subs = getattr(stream_client, "level_one_equity_subs", None)
                if subs is None:
                    return

                if callable(unsubs):
                    to_remove = sorted([s for s in applied_equities if s not in desired_list])
                    if to_remove:
                        await unsubs(to_remove)
                    to_add = sorted([s for s in desired_list if s not in applied_equities])
                    if to_add:
                        await subs(to_add, fields=equity_fields)
                else:
                    # Safe fallback: re-send the full list.
                    await subs(desired_list, fields=equity_fields)

                applied_equities = set(desired_list)

            async def _apply_futures_subs(stream_client: Any, desired: set[str]) -> None:
                """Apply futures subscription set to the streamer.

                Prefer unsubs if available; otherwise fall back to resubscribing the full desired list.
                """
                nonlocal applied_futures, futures_handler_added

                desired_list = sorted([s.upper() for s in desired if s])
                if not desired_list:
                    unsubs = getattr(stream_client, "level_one_futures_unsubs", None)
                    if callable(unsubs) and applied_futures:
                        await unsubs(sorted(list(applied_futures)))
                    applied_futures = set()
                    return

                if not futures_fields:
                    return

                if not futures_handler_added and message_handler is not None:
                    try:
                        stream_client.add_level_one_futures_handler(message_handler)
                        futures_handler_added = True
                    except Exception:
                        pass

                unsubs = getattr(stream_client, "level_one_futures_unsubs", None)
                subs = getattr(stream_client, "level_one_futures_subs", None)
                if subs is None:
                    return

                if callable(unsubs):
                    to_remove = sorted([s for s in applied_futures if s not in desired_list])
                    if to_remove:
                        await unsubs(to_remove)
                    to_add = sorted([s for s in desired_list if s not in applied_futures])
                    if to_add:
                        await subs(to_add, fields=futures_fields)
                else:
                    await subs(desired_list, fields=futures_fields)

                applied_futures = set(desired_list)

            control_queue: asyncio.Queue[dict] | None = None
            control_thread: threading.Thread | None = None

            while True:
                try:
                    first_message_seen = asyncio.Event()
                    stream_client: Any | None = None
                    control_task: asyncio.Task | None = None

                    # Reset per-connection state.
                    equity_handler_added = False
                    futures_handler_added = False
                    message_handler = None
                    equity_fields = []
                    futures_fields = []

                    def _handler(msg: object) -> None:
                        producer.process_message(msg)
                        _echo_message(msg)
                        try:
                            first_message_seen.set()
                        except Exception:
                            pass

                    message_handler = _handler

                    conn = connection
                    await refresh_from_db_async(conn)
                    conn = await ensure_token_async(conn, buffer_seconds=120)

                    token_state["token"] = {
                        "access_token": conn.access_token,
                        "refresh_token": conn.refresh_token,
                        "expires_at": int(conn.access_expires_at or 0),
                        "token_type": "Bearer",
                    }
                    token_state["creation_timestamp"] = int(conn.updated_at.timestamp()) if getattr(
                        conn, "updated_at", None
                    ) else int(time.time())

                    api_client = schwab_auth.client_from_access_functions(
                        api_key,
                        app_secret,
                        token_read_func=_read_token,
                        token_write_func=_write_token,
                        asyncio=True,
                    )

                    # Extra diagnostics: confirm streamer socket URL from user preferences
                    try:
                        prefs_resp = api_client.get_user_preferences()
                        if asyncio.iscoroutine(prefs_resp):
                            prefs_resp = await prefs_resp
                        prefs_json = (prefs_resp.json() if prefs_resp is not None else None) or {}
                        streamer_info = (prefs_json.get("streamerInfo") or [])
                        socket_url = (streamer_info[0] or {}).get("streamerSocketUrl") if streamer_info else None
                        logger.warning("Schwab user_preferences streamerSocketUrl=%s", socket_url)
                    except Exception as e:
                        logger.warning("Schwab user_preferences diagnostic failed: %s", e, exc_info=True)

                    stream_client = StreamClient(api_client, account_id=str(account_id))
                    await stream_client.login()
                    logger.warning("Schwab stream login OK (account_id=%s)", str(account_id))

                    # Optional QoS request (some streamer backends expect it).
                    # If schwab-py doesn't expose this, fail silently.
                    try:
                        qos_level = getattr(getattr(StreamClient, "QOSLevel", None), "EXPRESS", None)
                        qos_request = getattr(stream_client, "qos_request", None)
                        if qos_level is not None and qos_request is not None:
                            await qos_request(qos_level)
                            logger.warning("Schwab qos_request: %s", qos_level)
                    except Exception:
                        pass

                    keepalive_task: asyncio.Task | None = None
                    try:
                        sock = getattr(stream_client, "_socket", None)
                        if sock is not None:
                            keepalive_task = asyncio.create_task(_ws_keepalive(sock, interval=20.0))
                    except Exception:
                        keepalive_task = None

                    equity_fields = [
                        StreamClient.LevelOneEquityFields.SYMBOL,
                        StreamClient.LevelOneEquityFields.BID_PRICE,
                        StreamClient.LevelOneEquityFields.ASK_PRICE,
                        StreamClient.LevelOneEquityFields.LAST_PRICE,
                        StreamClient.LevelOneEquityFields.TOTAL_VOLUME,
                        StreamClient.LevelOneEquityFields.QUOTE_TIME_MILLIS,
                        StreamClient.LevelOneEquityFields.TRADE_TIME_MILLIS,
                    ]
                    futures_fields = [
                        StreamClient.LevelOneFuturesFields.SYMBOL,
                        StreamClient.LevelOneFuturesFields.BID_PRICE,
                        StreamClient.LevelOneFuturesFields.ASK_PRICE,
                        StreamClient.LevelOneFuturesFields.LAST_PRICE,
                        StreamClient.LevelOneFuturesFields.TOTAL_VOLUME,
                        StreamClient.LevelOneFuturesFields.QUOTE_TIME_MILLIS,
                        StreamClient.LevelOneFuturesFields.TRADE_TIME_MILLIS,
                    ]

                    # Start Redis control listener after a successful login and after fields are ready.
                    if control_queue is None:
                        control_queue = asyncio.Queue()
                    if control_thread is None:
                        control_thread = _start_pubsub_thread(user_id, control_queue, asyncio.get_running_loop())
                        logger.warning(
                            "Schwab control plane listening on %s (JSON: {action:add|remove|set, asset:EQUITY|FUTURE, symbols:[...]})",
                            _control_channel(user_id),
                        )

                    try:
                        # Apply initial desired subscription sets (safe: unsubs if supported, else resubscribe full).
                        await _apply_equity_subs(stream_client, current_equities)
                        await _apply_futures_subs(stream_client, current_futures)

                        async def _control_consumer() -> None:
                            nonlocal current_equities, current_futures
                            assert control_queue is not None
                            while True:
                                cmd = await control_queue.get()

                                action = (cmd.get("action") or "").strip().lower()
                                asset = (cmd.get("asset") or "").strip().upper()
                                raw_symbols = cmd.get("symbols") or []
                                if isinstance(raw_symbols, str):
                                    raw_symbols = [raw_symbols]
                                if not isinstance(raw_symbols, list):
                                    raw_symbols = []
                                symbols = [str(s).strip().upper() for s in raw_symbols if str(s).strip()]

                                if not action or not asset or (not symbols and action != "set"):
                                    continue

                                if asset in ("EQUITY", "EQUITIES", "STOCK", "INDEX"):
                                    # Strip leading '/' if the caller accidentally sent futures-style.
                                    symbols = [s.lstrip("/") for s in symbols if s]

                                    if action == "add":
                                        current_equities |= set(symbols)
                                    elif action == "remove":
                                        current_equities -= set(symbols)
                                    elif action == "set":
                                        current_equities = set(symbols)
                                    else:
                                        continue

                                    logger.warning(
                                        "Schwab control: %s EQUITY %s => %s",
                                        action,
                                        symbols,
                                        sorted(current_equities),
                                    )
                                    await _apply_equity_subs(stream_client, current_equities)

                                elif asset in ("FUTURE", "FUTURES"):
                                    # Ensure futures have a leading '/'.
                                    symbols = [s if s.startswith("/") else "/" + s.lstrip("/") for s in symbols if s]

                                    if action == "add":
                                        current_futures |= set(symbols)
                                    elif action == "remove":
                                        current_futures -= set(symbols)
                                    elif action == "set":
                                        current_futures = set(symbols)
                                    else:
                                        continue

                                    logger.warning(
                                        "Schwab control: %s FUTURE %s => %s",
                                        action,
                                        symbols,
                                        sorted(current_futures),
                                    )
                                    await _apply_futures_subs(stream_client, current_futures)

                        control_task = asyncio.create_task(_control_consumer())

                        try:
                            sock = getattr(stream_client, "_socket", None)
                            logger.warning(
                                "Schwab websocket state before loop: open=%s closed=%s close_code=%s close_reason=%r",
                                getattr(sock, "open", None),
                                getattr(sock, "closed", None),
                                getattr(sock, "close_code", None),
                                getattr(sock, "close_reason", None),
                            )
                        except Exception:
                            pass

                        logger.info("Listening for Schwab streaming messages")
                        while True:
                            await stream_client.handle_message()

                            if exit_after_first and first_message_seen.is_set():
                                logger.warning("Exiting Schwab stream after first message (--exit-after-first)")
                                return
                    finally:
                        # Best-effort clean shutdown so Ctrl-C doesn't leave
                        # websocket close tasks pending.
                        try:
                            if control_task is not None:
                                control_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await control_task
                            if keepalive_task is not None:
                                keepalive_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await keepalive_task
                            await stream_client.logout()
                        except Exception:
                            pass

                except asyncio.CancelledError:
                    raise
                except ConnectionClosed as exc:
                    code = getattr(exc, "code", None)
                    reason = getattr(exc, "reason", None)
                    # Code=1000 is a normal close; don't spam scary tracebacks.
                    if code in (1000, 1001):
                        logger.warning(
                            "Schwab websocket closed cleanly; reconnecting in %ss: code=%s reason=%r",
                            backoff,
                            code,
                            reason,
                        )
                    else:
                        logger.warning(
                            "Schwab websocket closed; reconnecting in %ss: code=%s reason=%r",
                            backoff,
                            code,
                            reason,
                            exc_info=True,
                        )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                except Exception as exc:
                    logger.warning(
                        "Schwab stream loop error; reconnecting in %ss: %s", backoff, exc, exc_info=True
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)

            # Unreachable, but keep structure explicit.
            # (asyncio.run will cancel tasks and exit.)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting Schwab stream user_id={user_id} "
                f"equities={equities or '-'} futures={futures or '-'}"
            )
        )
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))
