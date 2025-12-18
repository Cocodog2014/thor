import os
import sys
import time
import datetime as dt
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

import django  # noqa: E402

django.setup()

from LiveData.shared.redis_client import live_data_redis  # noqa: E402


def main():
    keys = [k.decode() if hasattr(k, "decode") else k for k in live_data_redis.client.scan_iter("live_data:balances:*")]
    print(f"Watching keys: {keys}")
    if not keys:
        print("No balances keys found")
        return

    preferred = [k for k in keys if "test" not in k.lower()]
    key = preferred[0] if preferred else keys[0]
    print(f"Selected key: {key}")
    while True:
        raw = live_data_redis.client.get(key)
        data = {} if raw is None else json.loads(raw)
        print(f"{dt.datetime.utcnow().isoformat()}Z {key} updated_at={data.get('updated_at')}")
        sys.stdout.flush()
        time.sleep(10)


if __name__ == "__main__":
    main()
