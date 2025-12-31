from __future__ import annotations

import os


def main() -> int:
    # Keep this script safe to run in any context.
    os.environ.setdefault("THOR_STACK_AUTO_START", "0")
    os.environ.setdefault("DJANGO_LOG_LEVEL", "ERROR")

    # Ensure Django is configured before importing any app modules.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

    import django

    django.setup()

    from LiveData.shared.redis_client import live_data_redis as r

    k = "live_data:active_session"
    print("type", r.client.type(k))
    print("get", r.client.get(k))
    print("hgetall", r.client.hgetall(k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
