#!/usr/bin/env python3
"""Utility to list Buffer profiles for quick ID lookup."""

import json
import os
import sys

import requests

API_URL = "https://api.bufferapp.com/1/profiles.json"


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    token = os.getenv("BUFFER_TOKEN")
    if not token:
        die("BUFFER_TOKEN environment variable is required.")

    try:
        resp = requests.get(
            API_URL,
            params={"access_token": token},
            headers={"User-Agent": "cf-autopost-feed/metrics"},
            timeout=20,
        )
    except requests.RequestException as exc:
        die(f"Failed to contact Buffer API: {exc}")

    if resp.status_code != 200:
        die(f"Buffer API returned {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except ValueError as exc:
        die(f"Unable to decode Buffer API response: {exc}")

    print(json.dumps(data, indent=2, sort_keys=True))
    print("\nTip: copy the \"id\" field for each profile and set PROFILE_IDS accordingly.")


if __name__ == "__main__":
    main()
