#!/usr/bin/env python3
"""
Polymarket Proof of Concept - Live Sports Markets (Simplified)
Shows all live sports markets with implied probabilities
"""
import requests
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

GAMMA_API = "https://gamma-api.polymarket.com"

def get_sports_leagues() -> List[Dict[str, Any]]:
    """Fetch sports leagues"""
    response = requests.get(f"{GAMMA_API}/sports", timeout=10)
    response.raise_for_status()
    leagues = response.json()

    # Filter to actual sports
    sports_keywords = ['nba', 'nfl', 'mlb', 'nhl', 'ncaa', 'epl', 'lal', 'ucl',
                       'tennis', 'golf', 'mma', 'ufc', 'boxing', 'f1', 'soccer']
    return [l for l in leagues if any(kw in l.get('sport', '').lower() for kw in sports_keywords)]

def calculate_time_to_expiration(end_date_iso: str) -> float:
    """Calculate minutes until expiration"""
    try:
        end_time = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (end_time - now).total_seconds() / 60
    except:
        return -1

def main():
    print("="*80)
    print("POLYMARKET LIVE SPORTS MARKETS")
    print("="*80)

    leagues = get_sports_leagues()
    print(f"\n✅ Found {len(leagues)} sports leagues\n")

    all_markets = []

    for league in leagues:
        league_name = league.get('sport', 'Unknown').upper()
        series_id = league.get('series', '')

        if not series_id:
            continue

        # Fetch active events
        params = {
            'series_id': series_id,
            'active': 'true',
            'closed': 'false',
            'order': 'startDate',
            'ascending': 'true',
            'limit': 100
        }

        try:
            response = requests.get(f"{GAMMA_API}/events", params=params, timeout=10)
            response.raise_for_status()
            events = response.json()

            if not events:
                continue

            print(f"\n{'='*80}")
            print(f"🏆 {league_name} - {len(events)} active events")
            print(f"{'='*80}")

            for event in events:
                title = event.get('title', '')
                start_time = event.get('startDate', '')
                end_time = event.get('endDate', '')
                markets = event.get('markets', [])

                time_to_exp = calculate_time_to_expiration(end_time)

                for market in markets:
                    question = market.get('question', '')

                    # Parse JSON strings
                    try:
                        outcomes = json.loads(market.get('outcomes', '[]'))
                        outcome_prices = json.loads(market.get('outcomePrices', '[]'))
                    except:
                        continue

                    print(f"\n📊 {title}")
                    print(f"   Question: {question}")
                    print(f"   Starts: {start_time}")
                    print(f"   Expires in: {time_to_exp:.1f} minutes")

                    for idx, outcome in enumerate(outcomes):
                        prob = float(outcome_prices[idx]) if idx < len(outcome_prices) else 0.0
                        print(f"   • {outcome}: {prob:.2%}")

                    market_data = {
                        'league': league_name,
                        'title': title,
                        'question': question,
                        'start_time': start_time,
                        'time_to_expiration_minutes': time_to_exp,
                        'outcomes': [
                            {'name': outcomes[i], 'implied_probability': float(outcome_prices[i])}
                            for i in range(min(len(outcomes), len(outcome_prices)))
                        ]
                    }
                    all_markets.append(market_data)

        except Exception as e:
            print(f"Error fetching {league_name}: {e}")

    print(f"\n{'='*80}")
    print(f"SUMMARY: {len(all_markets)} live markets found")
    print(f"{'='*80}\n")

    # Save to JSON
    with open('polymarket_live_markets.json', 'w') as f:
        json.dump(all_markets, f, indent=2)
    print(f"✅ Data saved to polymarket_live_markets.json\n")

if __name__ == "__main__":
    main()
