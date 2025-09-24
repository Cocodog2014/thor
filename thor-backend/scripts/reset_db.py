"""
Reset the Postgres database defined in .env (DB_NAME) by dropping and recreating it.
Uses admin credentials if provided (DB_ADMIN_USER/DB_ADMIN_PASSWORD),
otherwise falls back to DB_USER/DB_PASSWORD. Connects to the postgres maintenance
DB to perform operations.

Run: venv\Scripts\python.exe scripts\reset_db.py
"""
import os
import sys
import time
from contextlib import closing

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from decouple import config


def get_conn_params():
    dbname = config('DB_NAME', default='ThorData')
    host = config('DB_HOST', default='localhost')
    port = config('DB_PORT', default=5432, cast=int)

    # Prefer admin connection if provided, else fallback to app credentials
    user = config('DB_ADMIN_USER', default=config('DB_USER', default='postgres'))
    password = config('DB_ADMIN_PASSWORD', default=config('DB_PASSWORD', default='postgres'))

    return {
        'dbname': dbname,
        'host': host,
        'port': port,
        'user': user,
        'password': password,
    }


def connect_maintenance(user, password, host, port, maintenance_db='postgres'):
    return psycopg2.connect(dbname=maintenance_db, user=user, password=password, host=host, port=port)


def terminate_connections(cur, dbname):
    # Terminate other connections to allow drop
    cur.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
        """,
        (dbname,)
    )


def database_exists(cur, dbname) -> bool:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
    return cur.fetchone() is not None


def drop_create_db():
    params = get_conn_params()
    dbname = params['dbname']
    host = params['host']
    port = params['port']
    user = params['user']
    password = params['password']

    with closing(connect_maintenance(user, password, host, port)) as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with closing(conn.cursor()) as cur:
            if database_exists(cur, dbname):
                print(f"Dropping database {dbname}...")
                terminate_connections(cur, dbname)
                cur.execute(f'DROP DATABASE "{dbname}";')
                # small wait to ensure drop completes
                time.sleep(0.5)
            else:
                print(f"Database {dbname} does not exist; nothing to drop.")

            print(f"Creating database {dbname}...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
            print("Done.")


if __name__ == '__main__':
    try:
        drop_create_db()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
