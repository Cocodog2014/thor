import os
import sys
import time

from urllib.parse import urlparse

try:
    import redis  # type: ignore
except Exception as e:
    print("Redis client not installed. Please install with 'pip install redis'.", file=sys.stderr)
    raise

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def main() -> int:
    print(f"Connecting to {REDIS_URL} ...")
    r = redis.from_url(REDIS_URL, decode_responses=True)
    # Simple health check with retry
    for attempt in range(1, 6):
        try:
            pong = r.ping()
            print(f"PING -> {pong}")
            # write+read test
            r.set("thor:test:key", "ok", ex=30)
            val = r.get("thor:test:key")
            print(f"SET/GET -> {val}")
            return 0
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            time.sleep(1.5)
    return 1


if __name__ == "__main__":
    sys.exit(main())
