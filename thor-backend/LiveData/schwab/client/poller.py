import logging
import os
import time
from typing import Dict, Iterable, Tuple

from LiveData.schwab.models import BrokerConnection
from LiveData.schwab.utils import get_active_schwab_connection

logger = logging.getLogger(__name__)

# Environment controls
POLL_INTERVAL_SECONDS = int(os.environ.get("THOR_SCHWAB_POLL_INTERVAL", "15"))
ENABLE_POLLER = os.environ.get("THOR_ENABLE_SCHWAB_POLLER", "1") not in {"0", "false", "False", "no", ""}


def _iter_active_accounts():
    qs = BrokerConnection.objects.select_related("user").filter(broker=BrokerConnection.BROKER_SCHWAB)
    for conn in qs:
        user = conn.user
        if not get_active_schwab_connection(user):
            continue

        # Prefer cached hashValue; otherwise discover all accounts for the user.
        broker_account_id = (conn.broker_account_id or "").strip()
        if broker_account_id:
            yield user.id, broker_account_id
            continue

        try:
            from ActAndPos.live.brokers.schwab.sync import _fetch_account_numbers_map

            mapping = _fetch_account_numbers_map(user)
            for account_hash in set(mapping.values()):
                if account_hash:
                    yield user.id, str(account_hash)
        except Exception:
            logger.exception("Schwab poller could not resolve accountNumbers for user_id=%s", user.id)


def _iter_active_accounts_for_poll() -> Iterable[Tuple[int, str]]:
    return _iter_active_accounts()


def _poll_once():
    for user_id, broker_account_id in _iter_active_accounts_for_poll():
        try:
            from django.contrib.auth import get_user_model
            from ActAndPos.live.brokers.schwab.sync import sync_schwab_account

            User = get_user_model()
            user = User.objects.get(pk=user_id)

            sync_schwab_account(
                user=user,
                broker_account_id=str(broker_account_id),
                include_orders=False,
                publish_ws=True,
            )
        except Exception:
            logger.exception("❌ Schwab poll failed for user_id=%s account=%s", user_id, broker_account_id)
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
