#!/usr/bin/env python3
"""
Polymarket Sports Monitor - Simple POC
Fetches live individual game markets from Polymarket's Gamma API.

Uses tag_id=100639 (game bets) to get actual game-level markets
(e.g. "Lakers vs Celtics") instead of season-long futures.
Filters to only events where startDate is today and in the past
(game has already started).
"""

import json
import urllib.request
from datetime import datetime, timezone

GAMMA_EVENTS_API = "https://gamma-api.polymarket.com/events"
GAMMA_SPORTS_API = "https://gamma-api.polymarket.com/sports"

# tag_id for individual game bets (not futures)
GAME_BETS_TAG_ID = 100639


def fetch_leagues():
    """Fetch available leagues from the /sports endpoint."""
    req = urllib.request.Request(GAMMA_SPORTS_API)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "polymarket-monitor/1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    return data


def fetch_game_events(limit=100):
    """Fetch active game-level events using tag_id=100639."""
    params = (
        f"?tag_id={GAME_BETS_TAG_ID}"
        f"&active=true&closed=false"
        f"&limit={limit}"
        f"&order=startDate&ascending=false"
    )
    url = GAMMA_EVENTS_API + params

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "polymarket-monitor/1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    return data


def parse_start_date(event):
    """Parse the startDate field from an event. Returns None on failure."""
    start_date_str = event.get("startDate")
    if not start_date_str:
        return None
    try:
        return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def filter_started_today(events):
    """Filter to only events where startDate is today and in the past."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    started = []
    future = []
    older = []

    for event in events:
        start_date = parse_start_date(event)
        if start_date is None:
            continue

        if start_date < today_start:
            older.append(event)
        elif start_date <= now:
            started.append(event)
        else:
            future.append(event)

    return started, future, older


def main():
    print("Polymarket Live Game Monitor - POC")
    print("=" * 55)
    print()

    # Show available leagues
    leagues = fetch_leagues()
    league_names = [lg.get("sport", "?") for lg in leagues]
    print(f"Leagues tracked: {len(leagues)} ({', '.join(league_names[:10])}, ...)")
    print()

    # Fetch game-level events (not futures)
    events = fetch_game_events(limit=100)
    print(f"Total game events from API (tag_id={GAME_BETS_TAG_ID}): {len(events)}")

    # Filter: only today's games where startDate is in the past
    started, future, older = filter_started_today(events)
    now = datetime.now(timezone.utc)
    print(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"  Today, started (startDate in past):   {len(started)}")
    print(f"  Today, not started (future startDate): {len(future)}")
    print(f"  Older (before today):                  {len(older)}")
    print()

    if future:
        print("EXCLUDED - future games (not yet started):")
        print("-" * 55)
        for i, event in enumerate(future[:10]):
            title = event.get("title", "Unknown")
            sd = event.get("startDate", "N/A")
            print(f"  {i+1}. {title}")
            print(f"     startDate: {sd}")
        print()

    print(f"LIVE GAMES ({len(started)} markets):")
    print("-" * 55)
    for i, event in enumerate(started[:30]):
        title = event.get("title", "Unknown")
        sd = event.get("startDate", "N/A")
        print(f"  {i+1}. {title}")
        print(f"     startDate: {sd}")
    if len(started) > 30:
        print(f"  ... and {len(started) - 30} more")
    print()

    print(f"Result: {len(started)} live game markets (filtered from {len(events)} total)")


if __name__ == "__main__":
    main()
