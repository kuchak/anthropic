#!/usr/bin/env python3
"""
Polymarket Sports Monitor - Simple POC
Fetches active sports markets from Polymarket's Gamma API.
Only includes events where startDate is in the past (game has already started).
"""

import json
import urllib.request
from datetime import datetime, timezone

GAMMA_API = "https://gamma-api.polymarket.com/events"


def fetch_sports_events():
    """Fetch active sports events from Polymarket Gamma API."""
    params = "?active=true&closed=false&tag_slug=sports&limit=100"
    url = GAMMA_API + params

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "polymarket-monitor/1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    return data


def filter_started_events(events):
    """Filter to only include events where startDate is in the past."""
    now = datetime.now(timezone.utc)
    started = []
    skipped = 0

    for event in events:
        start_date_str = event.get("startDate")
        if not start_date_str:
            skipped += 1
            continue

        try:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            skipped += 1
            continue

        if start_date <= now:
            started.append(event)
        else:
            skipped += 1

    return started, skipped


def main():
    print("Polymarket Sports Monitor - POC")
    print("=" * 50)
    print()

    events = fetch_sports_events()
    print(f"Total events from API: {len(events)}")

    # Filter: only include events where startDate is in the past
    started_events, skipped = filter_started_events(events)
    print(f"Events with startDate in the past (started): {len(started_events)}")
    print(f"Events filtered out (future/missing startDate): {skipped}")
    print()

    # Show sample markets
    print("Live markets (game already started):")
    print("-" * 50)
    for i, event in enumerate(started_events[:20]):
        title = event.get("title", "Unknown")
        start_date = event.get("startDate", "N/A")
        print(f"  {i+1}. {title}")
        print(f"     startDate: {start_date}")
    print()

    if len(started_events) > 50:
        print(f"NOTE: {len(started_events)} started markets found.")
    else:
        print(f"OK: {len(started_events)} started markets found.")


if __name__ == "__main__":
    main()
