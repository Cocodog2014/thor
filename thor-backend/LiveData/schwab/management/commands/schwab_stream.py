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

            control_channel = _control_channel(user_id)
            control_queue: asyncio.Queue[dict] = asyncio.Queue()
            _start_pubsub_thread(user_id, control_queue, asyncio.get_running_loop())
            logger.warning(
                "Schwab control plane listening on %s (JSON: {action:add|remove|set, asset:EQUITY|FUTURE, symbols:[...]})",
                control_channel,
            )

            async def _apply_control_message(
                *,
                msg: dict,
                stream_client: Any | None,
                equity_fields: list[Any] | None = None,
                futures_fields: list[Any] | None = None,
                equity_handler: Any | None = None,
                futures_handler: Any | None = None,
                state: dict[str, Any] | None = None,
            ) -> None:
                action = (msg.get("action") or "").strip().lower()
                asset = (msg.get("asset") or "").strip().upper()
                raw_symbols = msg.get("symbols") or []
                if isinstance(raw_symbols, str):
                    raw_symbols = [raw_symbols]
                if not isinstance(raw_symbols, list):
                    raw_symbols = []
                symbols = [str(s).strip().lstrip("/").upper() for s in raw_symbols if str(s).strip()]
                if not action or not asset or not symbols and action != "set":
                    return

                if asset in {"FUTURE", "FUTURES"}:
                    target = desired_futures
                    subs = getattr(stream_client, "level_one_futures_subs", None) if stream_client else None
                    unsubs = getattr(stream_client, "level_one_futures_unsubs", None) if stream_client else None
                    fields = futures_fields
                    handler_adder_name = "add_level_one_futures_handler"
                    handler_key = "futures_handler_added"
                else:
                    # Default everything else to EQUITY stream
                    target = desired_equities
                    subs = getattr(stream_client, "level_one_equity_subs", None) if stream_client else None
                    unsubs = getattr(stream_client, "level_one_equity_unsubs", None) if stream_client else None
                    fields = equity_fields
                    handler_adder_name = "add_level_one_equity_handler"
                    handler_key = "equity_handler_added"

                def _ensure_handler() -> None:
                    if not stream_client or not state:
                        return
                    if state.get(handler_key):
                        return
                    adder = getattr(stream_client, handler_adder_name, None)
                    if not adder:
                        return
                    h = futures_handler if handler_key == "futures_handler_added" else equity_handler
                    if h is None:
                        return
                    try:
                        adder(h)
                        state[handler_key] = True
                    except Exception:
                        pass

                if action == "add":
                    new = [s for s in symbols if s not in target]
                    if not new:
                        return
                    target.update(new)
                    if subs and fields is not None:
                        _ensure_handler()
                        await subs(new, fields=fields)
                        logger.warning("Schwab control add %s %s", asset, new)
                    return

                if action == "remove":
                    rem = [s for s in symbols if s in target]
                    if not rem:
                        return
                    target.difference_update(rem)
                    if unsubs:
                        await unsubs(rem)
                        logger.warning("Schwab control remove %s %s", asset, rem)
                    return

                if action == "set":
                    newset = set(symbols)
                    to_remove = sorted([s for s in target if s not in newset])
                    to_add = sorted([s for s in newset if s not in target])
                    target.clear()
                    target.update(sorted(newset))
                    if stream_client:
                        if to_remove and unsubs:
                            await unsubs(to_remove)
                        if to_add and subs and fields is not None:
                            _ensure_handler()
                            await subs(to_add, fields=fields)
                        logger.warning("Schwab control set %s add=%s remove=%s", asset, to_add, to_remove)
                    return

            async def _drain_control_queue(*, stream_client: Any | None, **kwargs: Any) -> None:
                while True:
                    try:
                        msg = control_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    try:
                        await _apply_control_message(msg=msg, stream_client=stream_client, **kwargs)
                    except Exception:
                        logger.exception("Failed applying Schwab control message: %s", msg)

            while True:
                try:
                    first_message_seen = asyncio.Event()
                    stream_client: Any | None = None

                    state: dict[str, Any] = {
                        "equity_handler_added": False,
                        "futures_handler_added": False,
                    }

                    def _handler(msg: object) -> None:
                        producer.process_message(msg)
                        _echo_message(msg)
                        try:
                            first_message_seen.set()
                        except Exception:
                            pass

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

                    try:
                        # IMPORTANT: Handlers must be added BEFORE subscribing
                        equities_list = sorted(list(desired_equities))
                        futures_list = sorted(list(desired_futures))

                        if equities_list:
                            stream_client.add_level_one_equity_handler(_handler)
                            state["equity_handler_added"] = True
                            resp = await stream_client.level_one_equity_subs(
                                equities_list,
                                fields=equity_fields,
                            )
                            logger.warning("Schwab equity_subs sent symbols=%s resp=%s", equities_list, resp)

                        if futures_list:
                            stream_client.add_level_one_futures_handler(_handler)
                            state["futures_handler_added"] = True
                            resp = await stream_client.level_one_futures_subs(
                                futures_list,
                                fields=futures_fields,
                            )
                            logger.warning("Schwab futures_subs sent symbols=%s resp=%s", futures_list, resp)

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
                            msg_task = asyncio.create_task(stream_client.handle_message())
                            ctrl_task = asyncio.create_task(control_queue.get())
                            done, pending = await asyncio.wait(
                                {msg_task, ctrl_task},
                                return_when=asyncio.FIRST_COMPLETED,
                            )

                            if ctrl_task in done:
                                ctrl_msg = ctrl_task.result()
                                await _apply_control_message(
                                    msg=ctrl_msg,
                                    stream_client=stream_client,
                                    equity_fields=equity_fields,
                                    futures_fields=futures_fields,
                                    equity_handler=_handler,
                                    futures_handler=_handler,
                                    state=state,
                                )
                                msg_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await msg_task
                            else:
                                ctrl_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await ctrl_task

                            # If commands queued up, apply them promptly.
                            await _drain_control_queue(
                                stream_client=stream_client,
                                equity_fields=equity_fields,
                                futures_fields=futures_fields,
                                equity_handler=_handler,
                                futures_handler=_handler,
                                state=state,
                            )

                            if exit_after_first and first_message_seen.is_set():
                                logger.warning("Exiting Schwab stream after first message (--exit-after-first)")
                                return
                    finally:
                        # Best-effort clean shutdown so Ctrl-C doesn't leave
                        # websocket close tasks pending.
                        try:
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
                    # Apply any pending control messages even while disconnected.
                    with contextlib.suppress(Exception):
                        await _drain_control_queue(stream_client=None)

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
                    with contextlib.suppress(Exception):
                        await _drain_control_queue(stream_client=None)

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
