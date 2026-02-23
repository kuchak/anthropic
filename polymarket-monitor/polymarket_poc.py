#!/usr/bin/env python3
"""
Polymarket Proof of Concept - Live Sports Markets
Fetches all live sports markets with probabilities and order book data
"""
import requests
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

# API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

def get_sports_leagues() -> List[Dict[str, Any]]:
    """Fetch all sports leagues from Gamma API"""
    url = f"{GAMMA_API}/sports"
    print(f"\n🔍 Fetching sports leagues from {url}...")

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    leagues = response.json()

    # Filter to actual sports (exclude financial/political markets)
    sports_keywords = ['nba', 'nfl', 'mlb', 'nhl', 'ncaa', 'epl', 'lal', 'ucl',
                       'tennis', 'golf', 'mma', 'ufc', 'boxing', 'f1', 'soccer']

    sports_leagues = [l for l in leagues if any(kw in l.get('sport', '').lower() for kw in sports_keywords)]

    print(f"✅ Found {len(sports_leagues)} sports leagues (out of {len(leagues)} total)")
    return sports_leagues

def get_active_events(series_id: str, league_name: str) -> List[Dict[str, Any]]:
    """Fetch active events for a specific league/series"""
    url = f"{GAMMA_API}/events"
    params = {
        'series_id': series_id,
        'active': 'true',
        'closed': 'false',
        'order': 'startDate',
        'ascending': 'true',
        'limit': 100
    }

    print(f"  Fetching active events for {league_name} (series_id={series_id})...")
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        events = response.json()
        print(f"  Found {len(events)} active events")
        return events
    except Exception as e:
        print(f"  Error: {e}")
        return []

def get_order_book(token_id: str) -> Dict[str, Any]:
    """Fetch order book data from CLOB API for a specific token"""
    url = f"{CLOB_API}/book"
    params = {'token_id': token_id}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    Warning: Failed to get order book for token {token_id}: {e}")
        return {}

def calculate_time_to_expiration(end_date_iso: str) -> float:
    """Calculate minutes until market expiration"""
    try:
        end_time = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = end_time - now
        return delta.total_seconds() / 60
    except:
        return -1

def main():
    print("="*80)
    print("POLYMARKET PROOF OF CONCEPT - LIVE SPORTS MARKETS")
    print("="*80)

    # Fetch all sports leagues
    leagues = get_sports_leagues()

    all_markets = []
    total_events = 0

    # For each league, fetch active events
    for league in leagues:
        league_id = league.get('id', '')
        league_name = league.get('sport', 'Unknown').upper()
        series_id = league.get('series', '')

        if not series_id:
            continue

        print(f"\n📊 League: {league_name} (Series ID: {series_id})")

        try:
            events = get_active_events(series_id, league_name)
            total_events += len(events)

            # Process each event's markets
            for event in events:
                event_id = event.get('id', '')
                event_slug = event.get('slug', '')
                markets = event.get('markets', [])
                start_time = event.get('startDate', '')
                end_time = event.get('endDate', '')

                time_to_expiration = calculate_time_to_expiration(end_time)

                for market in markets:
                    market_slug = market.get('slug', '')
                    question = market.get('question', '')

                    # Parse JSON strings
                    outcomes_str = market.get('outcomes', '[]')
                    outcome_prices_str = market.get('outcomePrices', '[]')
                    clob_token_ids_str = market.get('clobTokenIds', '[]')

                    try:
                        outcomes = json.loads(outcomes_str)
                        outcome_prices = json.loads(outcome_prices_str)
                        clob_token_ids = json.loads(clob_token_ids_str)
                    except:
                        print(f"    Warning: Failed to parse market data for {question}")
                        continue

                    market_info = {
                        'league': league_name,
                        'event_id': event_id,
                        'event_slug': event_slug,
                        'market_slug': market_slug,
                        'question': question,
                        'start_time': start_time,
                        'end_time': end_time,
                        'time_to_expiration_minutes': time_to_expiration,
                        'outcomes': []
                    }

                    # Get order book data for each outcome
                    for idx, outcome in enumerate(outcomes):
                        outcome_name = outcome
                        implied_prob = float(outcome_prices[idx]) if idx < len(outcome_prices) else 0.0

                        # Get token_id for order book
                        token_id = clob_token_ids[idx] if idx < len(clob_token_ids) else None

                        best_bid = None
                        best_ask = None

                        if token_id:
                            order_book = get_order_book(token_id)
                            bids = order_book.get('bids', [])
                            asks = order_book.get('asks', [])

                            if bids and len(bids) > 0:
                                best_bid = float(bids[0].get('price', 0))
                            if asks and len(asks) > 0:
                                best_ask = float(asks[0].get('price', 0))

                        market_info['outcomes'].append({
                            'name': outcome_name,
                            'implied_probability': implied_prob,
                            'best_bid': best_bid,
                            'best_ask': best_ask,
                            'token_id': token_id
                        })

                    all_markets.append(market_info)

        except Exception as e:
            print(f"  ❌ Error fetching events for {league_name}: {e}")
            continue

    # Display all markets
    print("\n" + "="*80)
    print(f"SUMMARY: Found {len(all_markets)} live markets across {total_events} events")
    print("="*80)

    for market in all_markets:
        print(f"\n{'='*80}")
        print(f"🏆 League: {market['league']}")
        print(f"📅 Event: {market['event_slug']}")
        print(f"❓ Question: {market['question']}")
        print(f"⏰ Starts: {market['start_time']}")
        print(f"⏱️  Time to expiration: {market['time_to_expiration_minutes']:.1f} minutes")
        print(f"\n{'Outcomes:'}")

        for outcome in market['outcomes']:
            print(f"\n  📊 {outcome['name']}:")
            print(f"     Implied Probability: {outcome['implied_probability']:.2%}")
            print(f"     Best Bid: {outcome['best_bid']:.4f if outcome['best_bid'] else 'N/A'}")
            print(f"     Best Ask: {outcome['best_ask']:.4f if outcome['best_ask'] else 'N/A'}")

            if outcome['best_bid'] and outcome['best_ask']:
                spread = outcome['best_ask'] - outcome['best_bid']
                print(f"     Spread: {spread:.4f} ({spread*100:.2f}%)")

    # Save to JSON for inspection
    output_file = "polymarket_live_markets.json"
    with open(output_file, 'w') as f:
        json.dump(all_markets, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✅ Data saved to {output_file}")
    print(f"📊 Total markets: {len(all_markets)}")
    print("="*80)

if __name__ == "__main__":
    main()
