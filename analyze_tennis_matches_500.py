"""
Analyze 500 tennis matches for 90% crossing accuracy
- No double-counting (one match = one analysis)
- Ignore pre-match odds (only in-match crossings)
- Betting window = first touch → market close
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

class TennisMatchAnalyzer:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.tennis_series = "KXATPMATCH"

    def get_settled_tennis_markets(self, target_count: int = 1000) -> List[Dict]:
        """Get recent settled tennis markets (fetch in batches)"""
        print(f"📊 Fetching tennis markets from Kalshi...")

        all_settled = []
        cursor = None
        batch_size = 200

        try:
            while len(all_settled) < target_count:
                url = f"{self.base_url}/markets"
                params = {
                    'series_ticker': self.tennis_series,
                    'limit': batch_size
                }

                if cursor:
                    params['cursor'] = cursor

                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                markets = data.get('markets', [])
                if not markets:
                    break

                # Filter for settled markets
                settled = [
                    m for m in markets
                    if m.get('result') and m.get('settlement_value') is not None
                ]

                all_settled.extend(settled)
                print(f"📥 Fetched {len(all_settled)} settled markets so far...")

                # Check for next page
                cursor = data.get('cursor')
                if not cursor:
                    break

            print(f"✅ Found {len(all_settled)} total settled tennis markets")

            # Sort by close time (most recent first)
            markets_sorted = sorted(
                all_settled,
                key=lambda x: x.get('close_time', ''),
                reverse=True
            )

            return markets_sorted

        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return all_settled if all_settled else []

    def get_match_id(self, ticker: str) -> str:
        """Extract match ID from ticker (remove player suffix)"""
        # KXATPMATCH-26FEB08AUGMAN-AUG -> KXATPMATCH-26FEB08AUGMAN
        parts = ticker.rsplit('-', 1)
        return parts[0] if len(parts) > 1 else ticker

    def group_markets_by_match(self, markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group markets by match (both sides together)"""
        matches = defaultdict(list)

        for market in markets:
            match_id = self.get_match_id(market['ticker'])
            matches[match_id].append(market)

        return dict(matches)

    def get_market_trades(self, ticker: str, max_trades: int = 1000) -> List[Tuple[str, int]]:
        """Get trades for a specific market"""
        url = f"{self.base_url}/markets/trades"
        params = {
            'ticker': ticker,
            'limit': max_trades
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            trades = data.get('trades', [])

            # Extract timestamp and yes_price, sort by time
            trade_data = [
                (trade['created_time'], trade['yes_price'])
                for trade in trades
                if 'created_time' in trade and 'yes_price' in trade
            ]

            trade_data.sort(key=lambda x: x[0])
            return trade_data

        except Exception as e:
            print(f"  ⚠️  Error fetching trades: {e}")
            return []

    def get_match_start_time(self, trades_both_sides: List[List[Tuple[str, int]]]) -> Optional[str]:
        """Estimate match start time from first trades"""
        all_trades = []
        for trades in trades_both_sides:
            if trades:
                all_trades.extend(trades)

        if not all_trades:
            return None

        all_trades.sort(key=lambda x: x[0])

        # Use first trade time as proxy for match start
        # In reality, match might start a bit later, but this is conservative
        return all_trades[0][0]

    def find_first_90_touch(self, trades: List[Tuple[str, int]], close_time: str,
                            max_hours_before_close: int = 4) -> Optional[Dict]:
        """Find first touch of 90% within X hours of market close (in-match only)"""
        if not close_time:
            return None

        close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
        cutoff_dt = close_dt - timedelta(hours=max_hours_before_close)

        for timestamp, price in trades:
            trade_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # Only count if within X hours of close AND price >= 90
            if trade_dt >= cutoff_dt and price >= 90:
                return {
                    'timestamp': timestamp,
                    'price': price
                }

        return None

    def analyze_match(self, match_id: str, markets: List[Dict]) -> Optional[Dict]:
        """Analyze a single match (both sides)"""
        if not markets:
            return None

        # Get both sides
        side_a = markets[0]
        side_b = markets[1] if len(markets) > 1 else None

        ticker_a = side_a['ticker']
        ticker_b = side_b['ticker'] if side_b else None

        close_time = side_a.get('close_time')
        if not close_time:
            return None

        # Fetch trades for both sides
        trades_a = self.get_market_trades(ticker_a)
        trades_b = self.get_market_trades(ticker_b) if ticker_b else []

        if not trades_a and not trades_b:
            return None

        # Find 90% crossings on both sides (within 4 hours of close = in-match only)
        crossing_a = self.find_first_90_touch(trades_a, close_time, max_hours_before_close=4)
        crossing_b = self.find_first_90_touch(trades_b, close_time, max_hours_before_close=4) if trades_b else None

        # Determine which side crossed 90% first (if any)
        crossed_side = None
        first_crossing = None

        if crossing_a and crossing_b:
            # Both crossed - take earlier one
            if crossing_a['timestamp'] < crossing_b['timestamp']:
                crossed_side = 'A'
                first_crossing = crossing_a
            else:
                crossed_side = 'B'
                first_crossing = crossing_b
        elif crossing_a:
            crossed_side = 'A'
            first_crossing = crossing_a
        elif crossing_b:
            crossed_side = 'B'
            first_crossing = crossing_b

        if not first_crossing:
            # Neither side crossed 90% in-match
            return None

        # Determine match result
        market = side_a if crossed_side == 'A' else side_b
        settlement = market.get('settlement_value')

        # Calculate betting window (first touch → market close)
        betting_window_minutes = None
        betting_window_seconds = None

        if close_time:
            try:
                cross_time = datetime.fromisoformat(first_crossing['timestamp'].replace('Z', '+00:00'))
                close_time_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                time_diff = close_time_dt - cross_time
                betting_window_seconds = int(time_diff.total_seconds())
                betting_window_minutes = round(betting_window_seconds / 60, 1)
            except Exception as e:
                pass

        # Check if prediction was correct
        correct = settlement in [99, 100]

        return {
            'match_id': match_id,
            'ticker': market['ticker'],
            'title': market.get('title', ''),
            'result': market.get('result', ''),
            'settlement_value': settlement,
            'close_time': close_time,
            'crossed_90': True,
            'first_touch': first_crossing,
            'betting_window_minutes': betting_window_minutes,
            'betting_window_seconds': betting_window_seconds,
            'prediction_correct': correct,
            'trades_count_a': len(trades_a),
            'trades_count_b': len(trades_b)
        }

def main():
    analyzer = TennisMatchAnalyzer()

    # Get settled markets (need ~1000 markets to get 500 unique matches)
    markets = analyzer.get_settled_tennis_markets(target_count=1200)

    if not markets:
        print("❌ No markets found")
        return

    # Group by match
    print(f"\n📊 Grouping markets by match...")
    matches = analyzer.group_markets_by_match(markets)
    print(f"✅ Found {len(matches)} unique matches")

    # Analyze up to 500 matches
    num_to_analyze = min(500, len(matches))
    results = []

    print(f"\n🔍 Analyzing {num_to_analyze} matches...")

    match_items = list(matches.items())[:num_to_analyze]

    for i, (match_id, match_markets) in enumerate(match_items):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{num_to_analyze}...")

        result = analyzer.analyze_match(match_id, match_markets)
        if result:
            results.append(result)

    # Summary statistics
    print("\n" + "="*70)
    print("📊 SUMMARY STATISTICS")
    print("="*70)

    total_matches = num_to_analyze
    matches_crossed_90 = len(results)
    matches_correct = len([r for r in results if r['prediction_correct']])

    accuracy = (matches_correct / matches_crossed_90 * 100) if matches_crossed_90 else 0

    print(f"\n📈 Matches analyzed: {total_matches}")
    print(f"📈 Matches that crossed 90% (in-match): {matches_crossed_90}/{total_matches}")
    print(f"🎯 Correct predictions: {matches_correct}/{matches_crossed_90}")
    print(f"📊 Accuracy: {accuracy:.1f}%")

    # Betting window analysis
    betting_windows = [
        r['betting_window_minutes']
        for r in results
        if r['betting_window_minutes'] is not None
    ]

    if betting_windows:
        avg_window = sum(betting_windows) / len(betting_windows)
        min_window = min(betting_windows)
        max_window = max(betting_windows)

        print(f"\n⏱️  BETTING WINDOW ANALYSIS (first 90% touch → market close):")
        print(f"   Average: {avg_window:.1f} minutes")
        print(f"   Minimum: {min_window:.1f} minutes")
        print(f"   Maximum: {max_window:.1f} minutes")

    # False positives
    false_positives = [r for r in results if not r['prediction_correct']]

    if false_positives:
        print(f"\n⚠️  False positives (crossed 90% in-match but lost):")
        for r in false_positives:
            print(f"   - {r['ticker']}: {r['first_touch']['price']}¢ at {r['first_touch']['timestamp']}")

    # Save detailed results
    output = {
        'analysis_date': datetime.utcnow().isoformat(),
        'total_matches': total_matches,
        'crossed_90_count': matches_crossed_90,
        'accuracy': accuracy,
        'matches': results
    }

    with open('tennis_500_matches_analysis.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to: tennis_500_matches_analysis.json")

    # Create CSV
    print(f"\n📊 Creating detailed CSV...")
    import csv

    csv_file = 'tennis_500_matches_detailed.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        writer.writerow([
            'Match ID',
            'Ticker',
            'Title',
            'Result',
            'Settlement (¢)',
            'First 90% Time',
            'First 90% Price (¢)',
            'Market Close',
            'Betting Window (min)',
            'Betting Window (sec)',
            'Prediction Correct',
            'Trades Count'
        ])

        for r in results:
            writer.writerow([
                r['match_id'],
                r['ticker'],
                r['title'],
                r['result'],
                r['settlement_value'],
                r['first_touch']['timestamp'],
                r['first_touch']['price'],
                r['close_time'],
                r['betting_window_minutes'],
                r['betting_window_seconds'],
                'CORRECT' if r['prediction_correct'] else 'WRONG',
                r['trades_count_a'] + r['trades_count_b']
            ])

    print(f"✅ CSV saved to: {csv_file}")
    print("="*70)

if __name__ == '__main__':
    main()
