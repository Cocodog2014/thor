import logging
import os
import time
from datetime import datetime
from typing import Dict

from django.utils import timezone

from ActAndPos.models import Account
from LiveData.shared.redis_client import live_data_redis
from .trader import SchwabTraderAPI

logger = logging.getLogger(__name__)

# Environment controls
POLL_INTERVAL_SECONDS = int(os.environ.get("THOR_SCHWAB_POLL_INTERVAL", "15"))
ENABLE_POLLER = os.environ.get("THOR_ENABLE_SCHWAB_POLLER", "1") not in {"0", "false", "False", "no", ""}


def _iter_active_accounts():
    # Conservative filter: Schwab accounts with a non-empty broker_account_id
    qs = (
        Account.objects.select_related("user")
        .filter(broker="SCHWAB")
        .exclude(broker_account_id__isnull=True)
        .exclude(broker_account_id__exact="")
    )
    for acct in qs:
        yield acct


def _publish_balances(api: SchwabTraderAPI, account_hash: str, account_number: str | None):
    balances = api.fetch_balances(account_hash)
    if balances is None:
        return
    payload: Dict = {
        "account_hash": account_hash,
        "account_number": account_number,
        "updated_at": timezone.now().isoformat(),
        **(balances if isinstance(balances, dict) else {"balances": balances}),
    }
    live_data_redis.set_json(f"live_data:balances:{account_hash}", payload)
    live_data_redis.publish_balance(account_hash, payload)


def _publish_positions(api: SchwabTraderAPI, account_hash: str):
    # fetch_positions already normalizes, persists Positions, caches snapshot
    positions = api.fetch_positions(account_hash)
    live_data_redis.set_json(f"live_data:positions:{account_hash}", {
        "account_hash": account_hash,
        "positions": positions,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    })
    live_data_redis.publish_positions(account_hash, positions)


def _poll_once():
    seen_users: Dict[int, SchwabTraderAPI] = {}
    for acct in _iter_active_accounts():
        try:
            user = acct.user
            token = (
                user.get_active_schwab_token()
                if hasattr(user, "get_active_schwab_token")
                else getattr(user, "schwab_token", None)
            )
            if not token:
                logger.debug("Skip account %s: no active Schwab token", acct.account_number or acct.id)
                continue

            api = seen_users.get(user.id)
            if api is None:
                try:
                    api = SchwabTraderAPI(user)
                except Exception as e:
                    logger.warning("Skip user %s: Schwab API init failed: %s", user.id, e)
                    continue
                seen_users[user.id] = api

            account_id = acct.broker_account_id or acct.account_number
            if not account_id:
                logger.debug("Skip account %s: missing broker_account_id/account_number", acct.id)
                continue
            try:
                account_hash = api.resolve_account_hash(str(account_id))
            except Exception as e:
                logger.warning("Skip account %s (user %s): resolve hash failed: %s", account_id, user.id, e)
                continue

            try:
                _publish_balances(api, account_hash, acct.account_number)
            except Exception as e:
                logger.warning("Balances poll failed for %s: %s", account_hash, e)

            try:
                _publish_positions(api, account_hash)
            except Exception as e:
                logger.warning("Positions poll failed for %s: %s", account_hash, e)

        except Exception:
            logger.exception("❌ Schwab poll failed for %s", acct.account_number or acct.id)
            continue


def start_schwab_poller():
    if not ENABLE_POLLER:
        logger.info("💤 Schwab poller disabled via THOR_ENABLE_SCHWAB_POLLER")
        return

    logger.info("💰 Schwab balances/positions poller starting; interval=%ss", POLL_INTERVAL_SECONDS)
    while True:
        started = time.time()
        try:
            _poll_once()
        except Exception:
            logger.exception("Schwab poller iteration failed")
        else:
            # Heartbeat for visibility; logged each iteration
            logger.info("💓 Schwab poller alive (interval=%ss)", POLL_INTERVAL_SECONDS)
        elapsed = time.time() - started
        sleep_for = max(1, POLL_INTERVAL_SECONDS - int(elapsed))
        time.sleep(sleep_for)
