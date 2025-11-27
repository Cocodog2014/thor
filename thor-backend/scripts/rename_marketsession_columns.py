"""Bulk column renamer for FutureTrading_marketsession.

Run this once in maintenance mode to align legacy column names with the
current Django model fields. Safe to re-run; it skips any columns that
already match the target name.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django
from django.db import connection, transaction

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

FIELD_RENAMES: tuple[tuple[str, str], ...] = (
    ("market_high_percentage", "market_high_pct_open"),
    ("market_low_number", "market_low_open"),
    ("market_low_percentage", "market_low_pct_open"),
    ("market_close_number", "market_close"),
    ("market_close_percentage_high", "market_high_pct_close"),
    ("market_close_percentage_low", "market_low_pct_close"),
    ("market_range_number", "market_range"),
    ("market_range_percentage", "market_range_pct"),
)

TABLE_NAME = "FutureTrading_marketsession"
SCHEMA_NAME = "public"


def column_exists(cursor, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
          AND column_name = %s
        """,
        [SCHEMA_NAME, TABLE_NAME, column_name],
    )
    return cursor.fetchone() is not None


def rename_columns() -> None:
    django.setup()
    with connection.cursor() as cursor, transaction.atomic():
        for old_name, new_name in FIELD_RENAMES:
            old_exists = column_exists(cursor, old_name)
            new_exists = column_exists(cursor, new_name)

            if new_exists and not old_exists:
                print(f"[SKIP] {old_name!r} already renamed to {new_name!r}")
                continue

            if not old_exists and not new_exists:
                print(f"[WARN] neither {old_name!r} nor {new_name!r} exists; skipping")
                continue

            if new_exists:
                print(
                    f"[WARN] target column {new_name!r} exists alongside {old_name!r}; skipping to avoid data loss"
                )
                continue

            sql = f'ALTER TABLE "{TABLE_NAME}" RENAME COLUMN "{old_name}" TO "{new_name}";'
            cursor.execute(sql)
            print(f"[OK] renamed {old_name} -> {new_name}")


def main() -> None:
    try:
        rename_columns()
    except Exception as exc:  # pragma: no cover - manual utility
        print(f"[ERROR] rename failed: {exc}")
        raise


if __name__ == "__main__":
    main()
