"""Restore selected tables from the FutureTrading backup into ThorTrading tables."""
from __future__ import annotations

import pathlib
import subprocess
import sys

BACKUP_STAMP = "2025-12-03_115541"
TABLES = [
    "FutureTrading_instrumentcategory",
    "FutureTrading_tradinginstrument",
    "FutureTrading_contractweight",
    "FutureTrading_rolling52weekstats",
    "FutureTrading_signalstatvalue",
    "FutureTrading_targethighlowconfig",
]

DOCKER_SERVICE = "thor_postgres"
DB_NAME = "thor_db"
DB_USER = "thor_user"
BACKUP_DIR = pathlib.Path(__file__).resolve().parents[2] / "db_backups" / BACKUP_STAMP


def main() -> int:
    for table in TABLES:
        src = BACKUP_DIR / f"{table}.sql"
        if not src.exists():
            print(f"Missing backup file: {src}", file=sys.stderr)
            return 1
        sql = src.read_text(encoding="utf-8")
        sql = sql.replace("FutureTrading_", "ThorTrading_")
        print(f"Restoring {table} -> ThorTrading_*")
        proc = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                DOCKER_SERVICE,
                "psql",
                "-U",
                DB_USER,
                "-d",
                DB_NAME,
            ],
            input=sql.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            sys.stdout.write(proc.stdout.decode())
            sys.stderr.write(proc.stderr.decode() or f"Failed restoring {table}\n")
            return proc.returncode
    print("Restore complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
