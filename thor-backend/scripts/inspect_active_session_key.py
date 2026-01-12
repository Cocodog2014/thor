from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    # When executed as `python scripts/...py`, sys.path[0] is the scripts folder.
    # Add the project root (thor-backend/) so `thor_project` can be imported.
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Keep this script safe to run in any context.
    os.environ.setdefault("THOR_STACK_AUTO_START", "0")
    os.environ.setdefault("DJANGO_LOG_LEVEL", "ERROR")

    # Ensure Django is configured before importing any app modules.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

    import django

    django.setup()

    from LiveData.shared.redis_client import live_data_redis as r

    k = "live_data:active_session"
    kt = r.client.type(k)
    print("type", kt)

    if kt in {b"string", "string"}:
        print("get", r.client.get(k))
    elif kt in {b"hash", "hash"}:
        print("hgetall", r.client.hgetall(k))
    else:
        # Best-effort: show both without throwing.
        try:
            print("get", r.client.get(k))
        except Exception as exc:
            print("get_error", repr(exc))
        try:
            print("hgetall", r.client.hgetall(k))
        except Exception as exc:
            print("hgetall_error", repr(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
