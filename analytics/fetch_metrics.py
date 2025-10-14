#!/usr/bin/env python3
"""Fetch engagement metrics from Buffer and upsert analytics/metrics.json."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

import requests

API_ROOT = "https://api.bufferapp.com/1"
OUTPUT_PATH = "analytics/metrics.json"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "cf-autopost-feed/metrics"})


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def generate_sample_metrics(days: int = 7) -> List[Dict[str, object]]:
    """Synthesize predictable engagement data so the dashboard can render without Buffer access."""
    today = datetime.utcnow().date()
    services = ["linkedin", "facebook", "twitter"]
    records: List[Dict[str, object]] = []
    for offset in range(days):
        day = (today - timedelta(days=days - offset - 1)).isoformat()
        for idx, service in enumerate(services):
            base = (offset + 1) * (idx + 2)
            record = {
                "id": f"sample-{service}-{day}",
                "profile_id": f"sample-{service}",
                "service": service,
                "day": day,
                "text_len": 140 + idx * 5 + offset,
                "clicks": base + 2,
                "likes": base + 5,
                "shares": max(0, base // 3),
                "comments": max(0, base // 4),
            }
            records.append(record)
    return records


def load_existing() -> Dict[str, Dict[str, object]]:
    if not os.path.exists(OUTPUT_PATH):
        return {}
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as fh:
            items = json.load(fh)
    except (OSError, ValueError) as exc:
        die(f"Unable to read {OUTPUT_PATH}: {exc}")
    if not isinstance(items, list):
        die(f"{OUTPUT_PATH} must contain a JSON array.")
    store: Dict[str, Dict[str, object]] = {}
    for entry in items:
        if isinstance(entry, dict) and entry.get("id"):
            store[str(entry["id"])] = entry
    return store


def fetch_updates(token: str, profile_id: str, since_ts: int) -> Iterable[dict]:
    page = 1
    while True:
        try:
            resp = SESSION.get(
                f"{API_ROOT}/profiles/{profile_id}/updates/sent.json",
                params={
                    "access_token": token,
                    "page": page,
                    "count": 100,
                    "since": since_ts,
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            die(f"Network error for profile {profile_id}: {exc}")

        if resp.status_code != 200:
            die(
                f"Buffer API error for profile {profile_id}: "
                f"{resp.status_code} {resp.text}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            die(f"JSON decode error for profile {profile_id}: {exc}")

        updates = payload.get("updates")
        if updates is None:
            # some responses may return the list directly
            updates = payload if isinstance(payload, list) else []

        if not updates:
            break

        for update in updates:
            yield update

        # stop if fewer than requested (no more pages)
        if len(updates) < 100:
            break
        page += 1


def normalize_update(update: dict, profile_id: str) -> Dict[str, object]:
    update_id = str(update.get("id") or update.get("update_id") or "")
    if not update_id:
        return {}

    stats = update.get("statistics") or {}
    clicks = int(stats.get("clicks") or 0)
    likes = int(
        stats.get("likes")
        or stats.get("favorites")
        or stats.get("favorite")
        or 0
    )
    shares = int(stats.get("shares") or stats.get("retweets") or 0)
    comments = int(stats.get("comments") or 0)

    sent_at = (
        update.get("sent_at")
        or update.get("updated_at")
        or update.get("created_at")
        or update.get("due_at")
    )
    if isinstance(sent_at, (int, float)):
        dt = datetime.fromtimestamp(sent_at, tz=timezone.utc)
    else:
        dt = datetime.now(tz=timezone.utc)

    text = update.get("text") or update.get("body") or ""
    service = (
        (update.get("profile_service") or update.get("service") or "").lower()
    )
    if not service:
        service = "unknown"

    return {
        "id": update_id,
        "profile_id": profile_id,
        "service": service,
        "day": dt.strftime("%Y-%m-%d"),
        "text_len": len(text),
        "clicks": clicks,
        "likes": likes,
        "shares": shares,
        "comments": comments,
    }


def write_output(records: Iterable[Dict[str, object]]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    data = sorted(
        records,
        key=lambda r: (r.get("day", ""), r.get("id", "")),
    )
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    print(f"Wrote {len(data)} records to {OUTPUT_PATH}")


def main() -> None:
    token = os.getenv("BUFFER_TOKEN")
    profile_env = os.getenv("PROFILE_IDS")
    if not token or not profile_env:
        print("BUFFER_TOKEN or PROFILE_IDS not set. Writing sample metrics for testing.")
        write_output(generate_sample_metrics())
        return

    profile_ids = [p.strip() for p in profile_env.split(",") if p.strip()]
    if not profile_ids:
        print("PROFILE_IDS is empty. Writing sample metrics for testing.")
        write_output(generate_sample_metrics())
        return

    since_ts = int((datetime.utcnow() - timedelta(days=30)).timestamp())
    existing = load_existing()

    for profile_id in profile_ids:
        for raw in fetch_updates(token, profile_id, since_ts):
            normalized = normalize_update(raw, profile_id)
            if not normalized:
                continue
            existing[normalized["id"]] = normalized

    write_output(existing.values())


if __name__ == "__main__":
    main()
