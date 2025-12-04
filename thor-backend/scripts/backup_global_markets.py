"""Backup all GlobalMarkets_* tables to db_backups/<timestamp>."""
from __future__ import annotations

import datetime
import pathlib
import subprocess
import sys

DOCKER_SERVICE = "thor_postgres"
DB_NAME = "thor_db"
DB_USER = "thor_user"
PREFIX = "GlobalMarkets_%"
BACKUP_ROOT = pathlib.Path(__file__).resolve().parents[2] / "db_backups"


def list_tables() -> list[str]:
    query = (
        "SELECT tablename FROM pg_tables "
        "WHERE schemaname='public' AND tablename ILIKE '%s' ORDER BY tablename;" % PREFIX
    )
    cmd = [
        "docker",
        "exec",
        DOCKER_SERVICE,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-At",
        "-c",
        query,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or "Failed to list tables", file=sys.stderr)
        raise SystemExit(proc.returncode)
    tables = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not tables:
        print("No GlobalMarkets tables found", file=sys.stderr)
        raise SystemExit(1)
    return tables


def backup_tables(tables: list[str]) -> pathlib.Path:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest_dir = BACKUP_ROOT / timestamp
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Backing up {len(tables)} GlobalMarkets tables to {dest_dir} ...")
    for table in tables:
        outfile = dest_dir / f"{table}.sql"
        print(f"  -> {table}")
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
        with outfile.open("wb") as dump_fp:
            proc = subprocess.run(cmd, stdout=dump_fp, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(proc.stderr.decode() or f"pg_dump failed for {table}", file=sys.stderr)
            raise SystemExit(proc.returncode)
    print("Backup complete.")
    return dest_dir


def main() -> int:
    tables = list_tables()
    backup_tables(tables)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
