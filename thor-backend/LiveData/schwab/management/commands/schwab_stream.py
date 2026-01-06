# schwab_stream.py (management command)
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import socket
import threading
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

import ctypes

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from LiveData.schwab.models import BrokerConnection
from LiveData.schwab.client.streaming import SchwabStreamingProducer
from LiveData.schwab.client.tokens import ensure_valid_access_token
from LiveData.shared.redis_client import live_data_redis
from Instruments.models import Instrument, UserInstrumentWatchlistItem
from Instruments.services.schwab_fields import (
    SCHWAB_LEVEL_ONE_EQUITY_FIELDS,
    SCHWAB_LEVEL_ONE_FUTURES_FIELDS,
)

logger = logging.getLogger(__name__)

# --- schwab-py / websockets imports (these MUST exist in your env) ---
try:
    from schwab.auth import client_from_access_functions as schwab_client_from_access_functions
    from schwab.streaming import StreamClient
except Exception as exc:  # pragma: no cover
    StreamClient = None  # type: ignore
    schwab_client_from_access_functions = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    from websockets.exceptions import ConnectionClosed
except Exception:  # pragma: no cover
    ConnectionClosed = Exception  # type: ignore


# ---------------------------
# Helpers: CSV parsing + grouping
# ---------------------------
def _parse_csv(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [s.strip() for s in str(raw).split(",") if s and str(s).strip()]


def _group_subscriptions(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    equities: List[str] = []
    futures: List[str] = []
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        asset = (r.get("asset_type") or "").strip().upper()
        if not sym:
            continue
        if asset in ("EQUITY", "EQUITIES", "STOCK", "INDEX"):
            equities.append(sym.lstrip("/").upper())
        elif asset in ("FUTURE", "FUTURES"):
            s = sym.upper()
            if not s.startswith("/"):
                s = "/" + s.lstrip("/")
            futures.append(s)
    return equities, futures


def _load_watchlist_subscriptions(*, user_id: int, types_filter: set[str]) -> Tuple[List[str], List[str]]:
    qs = (
        UserInstrumentWatchlistItem.objects.select_related("instrument")
        .filter(user_id=user_id, enabled=True, stream=True, instrument__is_active=True)
        .order_by("order", "instrument__symbol")
    )

    # --types is a legacy CLI filter; interpret in terms of Schwab stream "assets"
    want_equities = False
    want_futures = False
    if types_filter:
        for t in types_filter:
            tt = (t or "").strip().upper()
            if tt in {"FUTURE", "FUTURES"}:
                want_futures = True
            elif tt in {"EQUITY", "EQUITIES", "STOCK", "STOCKS", "INDEX"}:
                want_equities = True

        if want_futures and not want_equities:
            qs = qs.filter(instrument__asset_type=Instrument.AssetType.FUTURE)
        elif want_equities and not want_futures:
            qs = qs.exclude(instrument__asset_type=Instrument.AssetType.FUTURE)

    equities: list[str] = []
    futures: list[str] = []

    for item in qs:
        inst = item.instrument
        symbol = (inst.symbol or "").strip().upper()
        if not symbol:
            continue

        quote_source = (getattr(inst, "quote_source", None) or "AUTO").upper()
        if quote_source not in {"AUTO", "SCHWAB"}:
            continue

        if inst.asset_type == Instrument.AssetType.FUTURE:
            futures.append(symbol if symbol.startswith("/") else "/" + symbol.lstrip("/"))
        else:
            equities.append(symbol.lstrip("/"))

    # De-dupe stable
    def _dedupe(xs: list[str]) -> list[str]:
        seen = set()
        out: list[str] = []
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return _dedupe(equities), _dedupe(futures)


# ---------------------------
# Control plane via Redis pubsub
# ---------------------------
def _control_channel(user_id: int) -> str:
    return f"live_data:subscriptions:schwab:{int(user_id)}"


def _start_pubsub_thread(user_id: int, queue: "asyncio.Queue[dict]", loop: asyncio.AbstractEventLoop) -> None:
    channel = _control_channel(user_id)

    def _worker() -> None:
        try:
            pubsub = live_data_redis.client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel)
            logger.warning("Schwab control-plane pubsub subscribed: %s", channel)

            for message in pubsub.listen():
                if not message or message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, (bytes, bytearray)):
                    try:
                        data = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                if not isinstance(data, str) or not data.strip():
                    continue
                try:
                    payload = json.loads(data)
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue

                # push into asyncio loop safely
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, payload)
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("Schwab control-plane thread died: %s", exc, exc_info=True)

    t = threading.Thread(target=_worker, name=f"schwab-control-{user_id}", daemon=True)
    t.start()


async def _ws_keepalive(sock: Any, interval: float = 20.0) -> None:
    """
    Best-effort keepalive for underlying websocket if schwab-py exposes it.
    This is optional and should never crash the stream.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            # Some ws objects support ping(); some don't.
            ping = getattr(sock, "ping", None)
            if callable(ping):
                res = ping()
                if asyncio.iscoroutine(res):
                    await res
        except asyncio.CancelledError:
            raise
        except Exception:
            continue


# ---------------------------
# Redis lock (single instance per user)
# ---------------------------
_RENEW_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('EXPIRE', KEYS[1], ARGV[2])
else
  return 0
end
"""

_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
"""


def _parse_lock_owner(value: object) -> tuple[str | None, int | None]:
    if not value:
        return None, None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return None, None
    if not isinstance(value, str):
        return None, None
    parts = value.split(":")
    if len(parts) < 2:
        return None, None
    host = (parts[0] or "").strip()
    try:
        pid = int(parts[1])
    except Exception:
        pid = None
    return host or None, pid


def _pid_exists_windows(pid: int) -> bool:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, int(pid))
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        err = ctypes.get_last_error()
    except Exception:
        err = 0
    return err == 5  # ERROR_ACCESS_DENIED


def _pid_exists(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            return _pid_exists_windows(int(pid))
        except Exception:
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _same_host(lock_host: str | None) -> bool:
    if not lock_host:
        return False
    local = (socket.gethostname() or "").strip().lower()
    remote = lock_host.strip().lower()
    if not local or not remote:
        return False
    if remote == local:
        return True
    return remote.split(".", 1)[0] == local.split(".", 1)[0]


# ---------------------------
# Django management command
# ---------------------------
class Command(BaseCommand):
    help = "Start Schwab streaming engine (writes ticks to Redis; supports live subscription control-plane)."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, default=1)
        parser.add_argument("--equities", type=str, default="")
        parser.add_argument("--futures", type=str, default="")
        parser.add_argument("--types", type=str, default="", help="Optional: filter DB subscriptions by asset type(s).")
        parser.add_argument("--echo-ticks", action="store_true", help="Echo normalized ticks to terminal.")
        parser.add_argument("--exit-after-first", action="store_true", help="Exit after first message received.")
        parser.add_argument("--lock-ttl", type=int, default=60, help="Redis lock TTL in seconds.")
        parser.add_argument("--lock-renew", type=int, default=20, help="How often to renew lock in seconds.")

    def handle(self, *args, **options):
        if _IMPORT_ERROR is not None or StreamClient is None or schwab_client_from_access_functions is None:
            raise CommandError(f"Missing schwab-py dependency imports: {_IMPORT_ERROR!r}")

        user_id: int = int(options.get("user_id") or 1)
        echo_ticks: bool = bool(options.get("echo_ticks"))
        exit_after_first: bool = bool(options.get("exit_after_first"))

        lock_ttl_seconds: int = int(options.get("lock_ttl") or 60)
        lock_renew_seconds: int = int(options.get("lock_renew") or 20)
        lock_key = f"live_data:lock:schwab_stream:{user_id}"
        lock_token = f"{socket.gethostname()}:{os.getpid()}"

        def _try_acquire_lock() -> bool:
            return bool(live_data_redis.client.set(lock_key, lock_token, nx=True, ex=lock_ttl_seconds))

        def _maybe_clear_stale_lock() -> bool:
            try:
                owner = live_data_redis.client.get(lock_key)
            except Exception:
                return False

            host, pid = _parse_lock_owner(owner)
            if not _same_host(host):
                return False
            if pid is None or _pid_exists(pid):
                return False

            try:
                deleted = live_data_redis.client.eval(_RELEASE_LUA, 1, lock_key, owner)
                if deleted:
                    logger.warning("Cleared stale Schwab stream lock user_id=%s owner=%r", user_id, owner)
                return bool(deleted)
            except Exception:
                # fallback
                try:
                    current = live_data_redis.client.get(lock_key)
                    if current == owner:
                        live_data_redis.client.delete(lock_key)
                        logger.warning("Cleared stale Schwab stream lock (fallback) user_id=%s owner=%r", user_id, owner)
                        return True
                except Exception:
                    return False
            return False

        # acquire lock
        acquired = False
        try:
            acquired = _try_acquire_lock()
            if not acquired:
                _maybe_clear_stale_lock()
                acquired = _try_acquire_lock()
        except Exception as exc:
            raise CommandError(f"Failed to acquire Schwab stream lock in Redis: {exc}")

        if not acquired:
            owner = None
            with contextlib.suppress(Exception):
                owner = live_data_redis.client.get(lock_key)
            raise CommandError(
                f"schwab_stream already running for user_id={user_id}. lock={lock_key} owner={owner!r}"
            )

        lock_stop = threading.Event()
        lock_lost = threading.Event()

        def _lock_renew_worker() -> None:
            while not lock_stop.wait(timeout=lock_renew_seconds):
                try:
                    ok = live_data_redis.client.eval(_RENEW_LUA, 1, lock_key, lock_token, lock_ttl_seconds)
                    if not ok:
                        lock_lost.set()
                        logger.error("Lost Schwab stream lock user_id=%s key=%s; stopping.", user_id, lock_key)
                        return
                except Exception as exc:
                    logger.warning("Failed to renew Schwab stream lock: %s", exc)

        renew_thread = threading.Thread(
            target=_lock_renew_worker,
            name=f"schwab-lock-renew-{user_id}",
            daemon=True,
        )
        renew_thread.start()

        try:
            # ----------------------------
            # Load initial subscriptions
            # ----------------------------
            equities: List[str] = _parse_csv(options.get("equities"))
            futures: List[str] = _parse_csv(options.get("futures"))

            if not equities and not futures:
                types_filter = set([t.strip().upper() for t in _parse_csv(options.get("types")) if t.strip()])
                equities, futures = _load_watchlist_subscriptions(user_id=user_id, types_filter=types_filter)

                if not equities and not futures:
                    logger.warning(
                        "No enabled stream watchlist items for user_id=%s; starting in IDLE mode (control-plane only).",
                        user_id,
                    )

            desired_equities: set[str] = set([s.upper().lstrip("/") for s in equities if s])
            desired_futures: set[str] = set([s.upper() if s.startswith("/") else "/" + s.upper().lstrip("/") for s in futures if s])

            connection = (
                BrokerConnection.objects.select_related("user")
                .filter(user_id=user_id, broker=BrokerConnection.BROKER_SCHWAB)
                .first()
            )
            if not connection:
                raise CommandError(f"No Schwab BrokerConnection found for user_id={user_id}")

            # Preflight token refresh
            connection = ensure_valid_access_token(connection, buffer_seconds=120)

            api_key = getattr(settings, "SCHWAB_CLIENT_ID", None) or getattr(settings, "SCHWAB_API_KEY", None)
            app_secret = getattr(settings, "SCHWAB_CLIENT_SECRET", None)
            if not api_key or not app_secret:
                raise CommandError("SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET must be set in settings/.env")

            account_id = connection.broker_account_id or None
            if not account_id:
                # Auto-resolve broker_account_id (hashValue)
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

                    account_id = acct_hash_map.get(str(account_number)) or api.resolve_account_hash(str(account_number))
                    if not account_id:
                        raise CommandError("Unable to resolve Schwab account hashValue (broker_account_id)")

                    connection.broker_account_id = str(account_id)
                    connection.save(update_fields=["broker_account_id", "updated_at"])
                except Exception as exc:
                    raise CommandError(f"Auto-resolve broker_account_id failed: {exc}")

            if not account_id:
                raise CommandError("Schwab connection missing broker_account_id; cannot start stream")

            # Token cache in-memory for schwab-py callbacks
            token_state: Dict[str, Any] = {
                "creation_timestamp": int(getattr(connection, "updated_at", None).timestamp())
                if getattr(connection, "updated_at", None)
                else int(time.time()),
                "token": {
                    "access_token": connection.access_token,
                    "refresh_token": connection.refresh_token,
                    "expires_at": int(connection.access_expires_at or 0),
                    "token_type": "Bearer",
                },
            }

            refresh_from_db_async = sync_to_async(lambda obj: obj.refresh_from_db(), thread_sensitive=True)
            ensure_token_async = sync_to_async(ensure_valid_access_token, thread_sensitive=True)

            async def _persist_tokens(payload: dict) -> None:
                await refresh_from_db_async(connection)
                connection.access_token = payload.get("access_token") or connection.access_token
                connection.refresh_token = payload.get("refresh_token") or connection.refresh_token
                if payload.get("expires_at") is not None:
                    connection.access_expires_at = int(payload.get("expires_at") or 0)
                await sync_to_async(connection.save, thread_sensitive=True)(
                    update_fields=["access_token", "refresh_token", "access_expires_at", "updated_at"]
                )

            def _read_token() -> dict:
                return deepcopy(token_state)

            def _write_token(token_obj: Any, *args, **kwargs) -> None:
                """
                schwab-py may pass token dict as {"token": {...}} or {...}
                and may include refresh_token via kwargs.
                """
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

                # Persist asynchronously (best effort)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_persist_tokens(token_state["token"].copy()))
                except Exception:
                    pass

            producer = SchwabStreamingProducer()

            def _echo_message(msg: object) -> None:
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
                        continue

            async def _run() -> None:
                backoff = 2
                max_backoff = 60

                control_queue: asyncio.Queue[dict] = asyncio.Queue()
                _start_pubsub_thread(user_id, control_queue, asyncio.get_running_loop())
                logger.warning("Schwab control plane channel=%s", _control_channel(user_id))

                current_equities: set[str] = set(desired_equities)
                current_futures: set[str] = set(desired_futures)

                applied_equities: set[str] = set()
                applied_futures: set[str] = set()

                async def _wait_for_subscriptions() -> None:
                    nonlocal current_equities, current_futures
                    while not current_equities and not current_futures:
                        if lock_lost.is_set():
                            raise CommandError(f"Lost Schwab stream lock key={lock_key}")
                        try:
                            cmd = await asyncio.wait_for(control_queue.get(), timeout=10)
                        except asyncio.TimeoutError:
                            continue
                        _apply_control_cmd(cmd, current_equities, current_futures)
                        if current_equities or current_futures:
                            logger.warning("Leaving idle mode; equities=%s futures=%s",
                                           sorted(current_equities), sorted(current_futures))
                            return

                def _apply_control_cmd(cmd: dict, equities_set: set[str], futures_set: set[str]) -> None:
                    action = (cmd.get("action") or "").strip().lower()
                    asset = (cmd.get("asset") or "").strip().upper()
                    raw_symbols = cmd.get("symbols") or []
                    if isinstance(raw_symbols, str):
                        raw_symbols = [raw_symbols]
                    if not isinstance(raw_symbols, list):
                        raw_symbols = []
                    symbols = [str(s).strip().upper() for s in raw_symbols if str(s).strip()]

                    if not action or not asset or (not symbols and action != "set"):
                        return

                    if asset in ("EQUITY", "EQUITIES", "STOCK", "INDEX"):
                        symbols = [s.lstrip("/") for s in symbols if s]
                        if action == "add":
                            equities_set |= set(symbols)
                        elif action == "remove":
                            equities_set -= set(symbols)
                        elif action == "set":
                            equities_set.clear()
                            equities_set |= set(symbols)

                    elif asset in ("FUTURE", "FUTURES"):
                        symbols = [s if s.startswith("/") else "/" + s.lstrip("/") for s in symbols if s]
                        if action == "add":
                            futures_set |= set(symbols)
                        elif action == "remove":
                            futures_set -= set(symbols)
                        elif action == "set":
                            futures_set.clear()
                            futures_set |= set(symbols)

                async def _apply_equity_subs(stream_client: Any, desired: set[str]) -> None:
                    nonlocal applied_equities
                    desired_list = sorted([s.upper().lstrip("/") for s in desired if s])
                    unsubs = getattr(stream_client, "level_one_equity_unsubs", None)
                    subs = getattr(stream_client, "level_one_equity_subs", None)
                    if not callable(subs):
                        return

                    fields = [
                        getattr(StreamClient.LevelOneEquityFields, name)
                        for name in SCHWAB_LEVEL_ONE_EQUITY_FIELDS
                        if hasattr(StreamClient.LevelOneEquityFields, name)
                    ]

                    if not desired_list:
                        if callable(unsubs) and applied_equities:
                            await unsubs(sorted(list(applied_equities)))
                        applied_equities = set()
                        return

                    if callable(unsubs):
                        to_remove = sorted([s for s in applied_equities if s not in desired_list])
                        if to_remove:
                            await unsubs(to_remove)
                        to_add = sorted([s for s in desired_list if s not in applied_equities])
                        if to_add:
                            await subs(to_add, fields=fields)
                    else:
                        await subs(desired_list, fields=fields)

                    applied_equities = set(desired_list)

                async def _apply_futures_subs(stream_client: Any, desired: set[str]) -> None:
                    nonlocal applied_futures
                    desired_list = sorted([s.upper() if s.startswith("/") else "/" + s.upper().lstrip("/") for s in desired if s])
                    unsubs = getattr(stream_client, "level_one_futures_unsubs", None)
                    subs = getattr(stream_client, "level_one_futures_subs", None)
                    if not callable(subs):
                        return

                    fields = [
                        getattr(StreamClient.LevelOneFuturesFields, name)
                        for name in SCHWAB_LEVEL_ONE_FUTURES_FIELDS
                        if hasattr(StreamClient.LevelOneFuturesFields, name)
                    ]

                    if not desired_list:
                        if callable(unsubs) and applied_futures:
                            await unsubs(sorted(list(applied_futures)))
                        applied_futures = set()
                        return

                    if callable(unsubs):
                        to_remove = sorted([s for s in applied_futures if s not in desired_list])
                        if to_remove:
                            await unsubs(to_remove)
                        to_add = sorted([s for s in desired_list if s not in applied_futures])
                        if to_add:
                            await subs(to_add, fields=fields)
                    else:
                        await subs(desired_list, fields=fields)

                    applied_futures = set(desired_list)

                while True:
                    try:
                        if not current_equities and not current_futures:
                            logger.warning("Schwab stream IDLE (no subscriptions). Waiting for control-plane updates...")
                            await _wait_for_subscriptions()

                        if lock_lost.is_set():
                            raise CommandError(f"Lost Schwab stream lock key={lock_key}")

                        first_message_seen = asyncio.Event()

                        def _handler(msg: object) -> None:
                            producer.process_message(msg)
                            _echo_message(msg)
                            with contextlib.suppress(Exception):
                                first_message_seen.set()

                        # refresh tokens each connect
                        conn = connection
                        await refresh_from_db_async(conn)
                        conn = await ensure_token_async(conn, buffer_seconds=120)

                        token_state["token"] = {
                            "access_token": conn.access_token,
                            "refresh_token": conn.refresh_token,
                            "expires_at": int(conn.access_expires_at or 0),
                            "token_type": "Bearer",
                        }
                        token_state["creation_timestamp"] = int(getattr(conn, "updated_at", None).timestamp()) if getattr(
                            conn, "updated_at", None
                        ) else int(time.time())

                        api_client = schwab_client_from_access_functions(
                            api_key,
                            app_secret,
                            token_read_func=_read_token,
                            token_write_func=_write_token,
                            asyncio=True,
                        )

                        stream_client = StreamClient(api_client, account_id=str(account_id))
                        stream_client.add_level_one_equity_handler(_handler)
                        stream_client.add_level_one_futures_handler(_handler)

                        await stream_client.login()
                        logger.warning("Schwab stream login OK (account_id=%s)", str(account_id))

                        keepalive_task: asyncio.Task | None = None
                        try:
                            sock = getattr(stream_client, "_socket", None)
                            if sock is not None:
                                keepalive_task = asyncio.create_task(_ws_keepalive(sock, interval=20.0))
                        except Exception:
                            keepalive_task = None

                        async def _control_consumer() -> None:
                            nonlocal current_equities, current_futures
                            while True:
                                cmd = await control_queue.get()
                                _apply_control_cmd(cmd, current_equities, current_futures)

                                if (cmd.get("asset") or "").strip().upper() in ("EQUITY", "EQUITIES", "STOCK", "INDEX"):
                                    logger.warning("Schwab control => equities=%s", sorted(current_equities))
                                    await _apply_equity_subs(stream_client, current_equities)
                                elif (cmd.get("asset") or "").strip().upper() in ("FUTURE", "FUTURES"):
                                    logger.warning("Schwab control => futures=%s", sorted(current_futures))
                                    await _apply_futures_subs(stream_client, current_futures)

                        control_task = asyncio.create_task(_control_consumer())

                        try:
                            # initial apply
                            await _apply_equity_subs(stream_client, current_equities)
                            await _apply_futures_subs(stream_client, current_futures)

                            logger.info("Listening for Schwab streaming messages")
                            while True:
                                await stream_client.handle_message()

                                if lock_lost.is_set():
                                    raise CommandError(f"Lost Schwab stream lock key={lock_key}")

                                if exit_after_first and first_message_seen.is_set():
                                    logger.warning("Exiting after first message (--exit-after-first)")
                                    return
                        finally:
                            with contextlib.suppress(Exception):
                                control_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await control_task
                            if keepalive_task is not None:
                                keepalive_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await keepalive_task
                            with contextlib.suppress(Exception):
                                await stream_client.logout()

                    except asyncio.CancelledError:
                        raise
                    except ConnectionClosed as exc:
                        code = getattr(exc, "code", None)
                        reason = getattr(exc, "reason", None)
                        logger.warning("Schwab websocket closed; reconnecting in %ss code=%s reason=%r",
                                       backoff, code, reason, exc_info=(code not in (1000, 1001)))
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, max_backoff)
                    except Exception as exc:
                        logger.warning("Schwab stream error; reconnecting in %ss: %s", backoff, exc, exc_info=True)
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, max_backoff)

            self.stdout.write(self.style.SUCCESS(
                f"Starting Schwab stream user_id={user_id} equities={equities or '-'} futures={futures or '-'}"
            ))

            try:
                asyncio.run(_run())
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("Schwab stream stopped (KeyboardInterrupt)"))

        finally:
            # stop renew + release lock
            lock_stop.set()
            with contextlib.suppress(Exception):
                renew_thread.join(timeout=2)

            with contextlib.suppress(Exception):
                live_data_redis.client.eval(_RELEASE_LUA, 1, lock_key, lock_token)
            # fallback
            with contextlib.suppress(Exception):
                current = live_data_redis.client.get(lock_key)
                if current == lock_token:
                    live_data_redis.client.delete(lock_key)
