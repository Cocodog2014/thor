from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ActAndPos.models import Account
from ActAndPos.models.snapshots import AccountDailySnapshot

try:
    from LiveData.schwab.client.trader import SchwabTraderAPI
except Exception:  # pragma: no cover - Schwab optional in some environments
    SchwabTraderAPI = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
	from LiveData.schwab.client.trader import SchwabTraderAPI as SchwabTraderAPIType
else:
	SchwabTraderAPIType = Any  # type: ignore


_SCHWAB_ACCOUNTS_CACHE: Dict[int, List[dict]] = {}


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else "0"))
    except Exception:
        return Decimal("0")


def _extract_from_schwab_payload(payload: dict) -> dict:
    """Normalize Schwab payloads (raw API, cached JSON, or Thor's dict)."""

    if not isinstance(payload, dict):
        return {}

    # Thor's Schwab service already returns the numeric fields we need.
    direct = {
        "net_liq": payload.get("net_liq"),
        "cash": payload.get("cash"),
        "equity": payload.get("equity"),
        "stock_buying_power": payload.get("stock_buying_power"),
        "option_buying_power": payload.get("option_buying_power"),
        "day_trading_buying_power": payload.get("day_trading_buying_power"),
    }
    if any(value is not None for value in direct.values()):
        return {field: _dec(value) for field, value in direct.items()}

    # Handle raw Schwab API JSON (nested under securitiesAccount balances).
    sa = payload.get("securitiesAccount")
    if not sa and isinstance(payload.get("accounts"), list) and payload["accounts"]:
        sa = payload["accounts"][0].get("securitiesAccount")

    if not isinstance(sa, dict):
        return {}

    current = sa.get("currentBalances") or {}
    initial = sa.get("initialBalances") or {}
    balances = current if isinstance(current, dict) and current else initial
    if not isinstance(balances, dict):
        balances = {}

    return {
        "net_liq": _dec(balances.get("liquidationValue") or balances.get("liquidation_value")),
        "cash": _dec(balances.get("cashBalance") or balances.get("cash_balance")),
        "equity": _dec(balances.get("equity")),
        "stock_buying_power": _dec(balances.get("buyingPower") or balances.get("buying_power")),
        "option_buying_power": _dec(balances.get("optionBuyingPower") or balances.get("option_buying_power")),
        "day_trading_buying_power": _dec(
            balances.get("dayTradingBuyingPower") or balances.get("day_trading_buying_power")
        ),
    }


def _get_schwab_live_balances(account: Account) -> Optional[dict]:
    """Fetch Schwab balances using the account number expected by the API."""

    if SchwabTraderAPI is None:
        return None

    try:
        api = SchwabTraderAPI(account.user)
    except Exception:
        return None

    accounts_payload = _get_schwab_accounts_payload(api, account.user_id)
    account_number = _resolve_schwab_account_number(account, accounts_payload)
    identifier_for_fetch = account_number or (account.broker_account_id or "").strip()

    raw: Optional[dict] = None
    if identifier_for_fetch:
        try:
            raw = api.fetch_balances(identifier_for_fetch)
        except Exception:
            raw = None

    if isinstance(raw, dict) and raw:
        extracted = _extract_from_schwab_payload(raw)
        if extracted:
            extracted["raw_payload"] = raw
            extracted["_account_number_used"] = account_number or identifier_for_fetch
            extracted["_source"] = "schwab_balances_api"
            return extracted

    account_payload = _match_account_payload(account, accounts_payload)
    if account_payload:
        extracted = _extract_from_schwab_payload(account_payload)
        if extracted:
            extracted["raw_payload"] = account_payload
            extracted["_source"] = "schwab_accounts_payload"
            if account_number:
                extracted["_account_number_used"] = account_number
            else:
                number = _extract_account_number(account_payload)
                if number:
                    extracted["_account_number_used"] = number
            return extracted

    return None


def _coerce_json(raw: Any) -> Optional[dict]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode()
        except Exception:
            return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


def _get_schwab_cached_balances(account: Account) -> Optional[dict]:
    """Read cached Schwab payloads from Redis/Django cache."""

    cache_keys = [
        f"schwab:balances:{account.user_id}:{account.broker_account_id}",
        f"schwab:balances:{account.broker_account_id}",
        f"schwab:account:{account.user_id}:{account.broker_account_id}",
        f"schwab:accounts:{account.user_id}",
    ]

    for key in cache_keys:
        payload = _coerce_json(cache.get(key))
        if not payload:
            continue
        extracted = _extract_from_schwab_payload(payload)
        if extracted:
            extracted["raw_payload"] = payload
            extracted["_cache_key_used"] = key
            return extracted

    return None


def _get_schwab_accounts_payload(api: "SchwabTraderAPIType", user_id: int) -> List[dict]:
    """Fetch /accounts payload once per user for the current command run."""

    if user_id in _SCHWAB_ACCOUNTS_CACHE:
        return _SCHWAB_ACCOUNTS_CACHE[user_id]

    try:
        payload = api.fetch_accounts() or []
    except Exception:
        payload = []

    _SCHWAB_ACCOUNTS_CACHE[user_id] = payload
    return payload


def _extract_account_number(payload: dict) -> Optional[str]:
    sec = (payload or {}).get("securitiesAccount", {}) or {}
    number = sec.get("accountNumber") or payload.get("accountNumber")
    if number is None:
        return None
    return str(number)


def _payload_identifiers(payload: dict) -> List[str]:
    sec = (payload or {}).get("securitiesAccount", {}) or {}
    candidates = [
        payload.get("hashValue"),
        sec.get("hashValue"),
        payload.get("accountId"),
        sec.get("accountId"),
        payload.get("accountNumber"),
        sec.get("accountNumber"),
    ]
    identifiers: List[str] = []
    for candidate in candidates:
        if candidate is None:
            continue
        identifiers.append(str(candidate).strip())
    return identifiers


def _match_account_payload(account: Account, accounts_payload: List[dict]) -> Optional[dict]:
    target = (account.broker_account_id or "").strip()
    if not target:
        return None

    target_lower = target.lower()

    for entry in accounts_payload:
        for identifier in _payload_identifiers(entry):
            if identifier.lower() == target_lower:
                return entry
    return None


def _resolve_schwab_account_number(account: Account, accounts_payload: List[dict]) -> Optional[str]:
    broker_id = (account.broker_account_id or "").strip()
    if not broker_id:
        return None

    if broker_id.isdigit():
        return broker_id

    matched = _match_account_payload(account, accounts_payload)
    if not matched:
        return None

    return _extract_account_number(matched)


class Command(BaseCommand):
    help = (
        "Create one daily snapshot per account.\n"
        "PAPER: snapshot from Account (DB).\n"
        "SCHWAB: snapshot strictly from Schwab live fetch or Redis/cache (no DB fallback)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="trading_date",
            default=None,
            help="Trading date YYYY-MM-DD (default: today).",
        )
        parser.add_argument(
            "--broker",
            dest="broker",
            default="ALL",
            help="Filter broker: ALL | SCHWAB | PAPER",
        )
        parser.add_argument(
            "--source",
            dest="source",
            default="AUTO",
            help="For SCHWAB only: AUTO | SCHWAB | REDIS (AUTO tries SCHWAB then REDIS).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite snapshot if it already exists for (account, date).",
        )

    def handle(self, *args, **options):
        _SCHWAB_ACCOUNTS_CACHE.clear()

        tz_now = timezone.localtime(timezone.now())
        trading_date: date
        if options.get("trading_date"):
            trading_date = date.fromisoformat(options["trading_date"])
        else:
            trading_date = tz_now.date()

        broker_filter = (options.get("broker") or "ALL").upper().strip()
        source = (options.get("source") or "AUTO").upper().strip()
        overwrite = bool(options.get("overwrite"))

        accounts_qs = Account.objects.select_related("user")
        if broker_filter in ("SCHWAB", "PAPER"):
            accounts_qs = accounts_qs.filter(broker=broker_filter)

        accounts = list(accounts_qs)
        if not accounts:
            self.stdout.write(self.style.WARNING("No accounts found for snapshot."))
            return

        self.stdout.write(
            f"Snapshot date={trading_date} broker={broker_filter} source={source} "
            f"overwrite={overwrite} accounts={len(accounts)}"
        )

        created = updated = skipped = 0
        schwab_live_ok = schwab_cache_ok = schwab_fail = 0

        for account in accounts:
            fields: Optional[dict] = None

            if account.broker == "PAPER":
                fields = {
                    "net_liq": _dec(account.net_liq),
                    "cash": _dec(account.cash),
                    "equity": _dec(account.equity),
                    "stock_buying_power": _dec(account.stock_buying_power),
                    "option_buying_power": _dec(account.option_buying_power),
                    "day_trading_buying_power": _dec(account.day_trading_buying_power),
                    "raw_payload": None,
                }
            elif account.broker == "SCHWAB":
                if source in ("AUTO", "SCHWAB"):
                    fields = _get_schwab_live_balances(account)
                    if fields:
                        schwab_live_ok += 1

                if not fields and source in ("AUTO", "REDIS"):
                    fields = _get_schwab_cached_balances(account)
                    if fields:
                        schwab_cache_ok += 1

                if not fields:
                    schwab_fail += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping SCHWAB account={account.id} (no Schwab live/cache balances)."
                        )
                    )
                    continue
            else:
                self.stdout.write(self.style.WARNING(f"Skipping account={account.id} broker={account.broker}"))
                continue

            defaults = {
                "net_liq": fields["net_liq"],
                "cash": fields["cash"],
                "equity": fields["equity"],
                "stock_buying_power": fields["stock_buying_power"],
                "option_buying_power": fields["option_buying_power"],
                "day_trading_buying_power": fields["day_trading_buying_power"],
                "raw_payload": fields.get("raw_payload"),
                "captured_at": timezone.now(),
            }

            with transaction.atomic():
                existing = AccountDailySnapshot.objects.filter(
                    account=account,
                    trading_date=trading_date,
                ).first()

                if existing and not overwrite:
                    skipped += 1
                    continue

                if existing and overwrite:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                    continue

                AccountDailySnapshot.objects.create(
                    account=account,
                    trading_date=trading_date,
                    **defaults,
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped} "
                f"schwab_live_ok={schwab_live_ok} schwab_cache_ok={schwab_cache_ok} schwab_fail={schwab_fail}"
            )
        )
