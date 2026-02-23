#!/usr/bin/env python3
"""Inspect Polymarket API responses to understand data structure"""
import requests
import json

GAMMA_API = "https://gamma-api.polymarket.com"

# Fetch sports leagues
print("Fetching sports leagues...")
response = requests.get(f"{GAMMA_API}/sports")
leagues = response.json()

print(f"\n{'='*80}")
print(f"Sports Leagues Response (first 3):")
print(f"{'='*80}")
for league in leagues[:3]:
    print(json.dumps(league, indent=2))

# Find a league with active events
print(f"\n{'='*80}")
print("Finding leagues with active events...")
print(f"{'='*80}")

for league in leagues[:50]:
    league_id = league.get('id', '')
    params = {
        'series_id': league_id,
        'active': 'true',
        'closed': 'false'
    }
    response = requests.get(f"{GAMMA_API}/events", params=params)
    events = response.json()

    if events and len(events) > 0:
        print(f"\n✅ Found {len(events)} events for league ID {league_id}")
        print(f"League data: {json.dumps(league, indent=2)}")
        print(f"\nFirst event:")
        print(json.dumps(events[0], indent=2))
        break
