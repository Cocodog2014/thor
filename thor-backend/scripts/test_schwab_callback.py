"""Quick helper to simulate a Schwab OAuth callback.

Run this while the Django dev server is up to confirm that
/api/schwab/oauth/callback/ is reachable and logging requests.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call the Schwab OAuth callback endpoint with a test code.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the backend (default: %(default)s)",
    )
    parser.add_argument(
        "--code",
        default="TEST-CODE",
        help="Authorization code to send in the query string.",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Optional OAuth state value to include.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Request timeout in seconds (default: %(default)s)",
    )
    return parser.parse_args()


def pretty_print_payload(payload: Any) -> None:
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)


def main() -> None:
    args = parse_args()
    callback_url = args.base_url.rstrip("/") + "/api/schwab/oauth/callback/"
    params = {"code": args.code}

    if args.state:
        params["state"] = args.state

    print(f"Calling {callback_url} with params={params}")

    try:
        response = requests.get(callback_url, params=params, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
        return

    print(f"Status: {response.status_code}")
    print(f"Final URL: {response.url}")

    try:
        pretty_print_payload(response.json())
    except ValueError:
        print(response.text)


if __name__ == "__main__":
    main()
