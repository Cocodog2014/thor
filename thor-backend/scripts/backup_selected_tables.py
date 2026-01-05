"""Utility script to dump selected Postgres tables via docker exec.

Usage:
    python scripts/backup_selected_tables.py
"""
from __future__ import annotations

import datetime
import pathlib
import subprocess
import sys

TABLES = [
    "FutureTrading_contractweight",
    "FutureTrading_instrumentcategory",
    "FutureTrading_signalstatvalue",
    "FutureTrading_targethighlowconfig",
    "FutureTrading_tradinginstrument",
]

BACKUP_ROOT = pathlib.Path(__file__).resolve().parents[2] / "db_backups"
DOCKER_SERVICE = "thor_postgres"
DB_NAME = "thor_db"
DB_USER = "thor_user"


def main() -> int:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest_dir = BACKUP_ROOT / timestamp
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Backing up {len(TABLES)} tables to {dest_dir} ...")

    for table in TABLES:
        outfile = dest_dir / f"{table}.sql"
        cmd = [
            "docker",
            "exec",
            DOCKER_SERVICE,
            "pg_dump",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-t",
            f'public."{table}"',
            "--data-only",
            "--column-inserts",
        ]
        print(f"  -> {table}")
        with outfile.open("wb") as dump_fp:
            proc = subprocess.run(cmd, stdout=dump_fp, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stderr.decode() or f"pg_dump failed for {table}")
            return proc.returncode

    print("Backup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
