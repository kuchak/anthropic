"""
Multi-sport 90% crossing analysis
Test if 90% threshold is universal or sport-specific
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter

class MultiSportAnalyzer:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"

        # Define sports series to analyze (using actual Kalshi tickers)
        self.sports_series = {
            'Tennis': 'KXATPMATCH',
            'College Basketball': 'KXNCAAMBGAME',
            'NBA': 'KXNBAGAME',
            'NFL': 'KXNFLGAME',
            'NHL': 'KXNHLGAME',
            'MLB': 'KXMLBGAME',
            'Premier League': 'KXEPLGAME',
            'La Liga': 'KXLALIGAGAME',
            'Champions League': 'KXUCLGAME',
            'Cricket IPL': 'KXIPLGAME',
            'Esports - LoL': 'KXLOLGAME',
            'Esports - CS:GO': 'KXCSGOGAME',
            'ABA Basketball': 'KXABAGAME',
            'ACB Basketball': 'KXACBGAME',
            'AHL Hockey': 'KXAHLGAME',
            'Australian Soccer': 'KXALEAGUEGAME',
        }

    def discover_sports_series(self) -> List[str]:
        """Discover available sports series on Kalshi"""
        print("🔍 Discovering available sports series...")

        url = f"{self.base_url}/series"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            all_series = data.get('series', [])

            # Filter for sports-related series
            sports_keywords = ['match', 'game', 'nba', 'nfl', 'nhl', 'mlb', 'ncaa',
                             'soccer', 'football', 'cricket', 'tennis', 'esport',
                             'lol', 'dota', 'csgo', 'high']

            sports_series = []
            for series in all_series:
                ticker = series.get('ticker', '').lower()
                title = series.get('title', '').lower()

                if any(keyword in ticker or keyword in title for keyword in sports_keywords):
                    sports_series.append({
                        'ticker': series.get('ticker'),
                        'title': series.get('title'),
                        'category': series.get('category', 'Unknown')
                    })

            print(f"✅ Found {len(sports_series)} sports-related series")
            return sports_series

        except Exception as e:
            print(f"❌ Error discovering series: {e}")
            return []

    def get_settled_markets(self, series_ticker: str, target_count: int = 100) -> List[Dict]:
        """Get settled markets for a specific series"""
        all_settled = []
        cursor = None
        batch_size = 200

        try:
            while len(all_settled) < target_count:
                url = f"{self.base_url}/markets"
                params = {
                    'series_ticker': series_ticker,
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

                cursor = data.get('cursor')
                if not cursor:
                    break

            # Sort by close time (most recent first)
            markets_sorted = sorted(
                all_settled,
                key=lambda x: x.get('close_time', ''),
                reverse=True
            )

            return markets_sorted[:target_count]

        except Exception as e:
            print(f"  ⚠️  Error fetching {series_ticker}: {e}")
            return all_settled if all_settled else []

    def get_match_id(self, ticker: str) -> str:
        """Extract match ID from ticker (remove player/team suffix)"""
        parts = ticker.rsplit('-', 1)
        return parts[0] if len(parts) > 1 else ticker

    def group_markets_by_match(self, markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group markets by match"""
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

            trade_data = [
                (trade['created_time'], trade['yes_price'])
                for trade in trades
                if 'created_time' in trade and 'yes_price' in trade
            ]

            trade_data.sort(key=lambda x: x[0])
            return trade_data

        except Exception as e:
            return []

    def find_first_90_touch(self, trades: List[Tuple[str, int]], close_time: str,
                            max_hours_before_close: int = 4) -> Optional[Dict]:
        """Find first touch of 90% within X hours of market close"""
        if not close_time:
            return None

        close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
        cutoff_dt = close_dt - timedelta(hours=max_hours_before_close)

        for timestamp, price in trades:
            trade_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            if trade_dt >= cutoff_dt and price >= 90:
                return {
                    'timestamp': timestamp,
                    'price': price
                }

        return None

    def analyze_match(self, match_id: str, markets: List[Dict]) -> Optional[Dict]:
        """Analyze a single match"""
        if not markets:
            return None

        side_a = markets[0]
        side_b = markets[1] if len(markets) > 1 else None

        ticker_a = side_a['ticker']
        ticker_b = side_b['ticker'] if side_b else None

        close_time = side_a.get('close_time')
        if not close_time:
            return None

        # Fetch trades
        trades_a = self.get_market_trades(ticker_a)
        trades_b = self.get_market_trades(ticker_b) if ticker_b else []

        if not trades_a and not trades_b:
            return None

        # Find 90% crossings
        crossing_a = self.find_first_90_touch(trades_a, close_time, max_hours_before_close=4)
        crossing_b = self.find_first_90_touch(trades_b, close_time, max_hours_before_close=4) if trades_b else None

        # Determine which side crossed first
        crossed_side = None
        first_crossing = None

        if crossing_a and crossing_b:
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
            return None

        # Get result
        market = side_a if crossed_side == 'A' else side_b
        settlement = market.get('settlement_value')

        # Calculate betting window
        betting_window_minutes = None
        if close_time:
            try:
                cross_time = datetime.fromisoformat(first_crossing['timestamp'].replace('Z', '+00:00'))
                close_time_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                time_diff = close_time_dt - cross_time
                betting_window_minutes = round(time_diff.total_seconds() / 60, 1)
            except:
                pass

        correct = settlement in [99, 100]

        return {
            'match_id': match_id,
            'ticker': market['ticker'],
            'title': market.get('title', ''),
            'settlement_value': settlement,
            'first_touch': first_crossing,
            'betting_window_minutes': betting_window_minutes,
            'prediction_correct': correct
        }

    def analyze_sport(self, sport_name: str, series_ticker: str, target_matches: int = 100):
        """Analyze a single sport"""
        print(f"\n{'='*70}")
        print(f"🏀 Analyzing: {sport_name} ({series_ticker})")
        print('='*70)

        # Get markets
        markets = self.get_settled_markets(series_ticker, target_count=target_matches * 2)

        if not markets:
            print(f"  ⚠️  No settled markets found")
            return None

        print(f"  📥 Found {len(markets)} settled markets")

        # Group by match
        matches = self.group_markets_by_match(markets)
        print(f"  🔢 Found {len(matches)} unique matches")

        # Analyze matches
        results = []
        match_items = list(matches.items())[:target_matches]

        for match_id, match_markets in match_items:
            result = self.analyze_match(match_id, match_markets)
            if result:
                results.append(result)

        if not results:
            print(f"  ⚠️  No matches crossed 90%")
            return None

        # Calculate stats
        total_analyzed = min(target_matches, len(matches))
        crossed_90 = len(results)
        correct = len([r for r in results if r['prediction_correct']])
        accuracy = correct / crossed_90 * 100 if crossed_90 > 0 else 0

        # Betting windows
        windows = [r['betting_window_minutes'] for r in results if r['betting_window_minutes']]
        avg_window = sum(windows) / len(windows) if windows else 0

        print(f"\n  📊 Results:")
        print(f"     Matches analyzed: {total_analyzed}")
        print(f"     Crossed 90%: {crossed_90}/{total_analyzed} ({crossed_90/total_analyzed*100:.1f}%)")
        print(f"     Accuracy: {correct}/{crossed_90} = {accuracy:.1f}%")
        print(f"     Avg betting window: {avg_window:.1f} min")

        return {
            'sport': sport_name,
            'series_ticker': series_ticker,
            'matches_analyzed': total_analyzed,
            'crossed_90': crossed_90,
            'correct_predictions': correct,
            'accuracy': accuracy,
            'avg_betting_window': avg_window,
            'results': results
        }

def main():
    analyzer = MultiSportAnalyzer()

    # Discover available sports
    available_series = analyzer.discover_sports_series()

    print("\n" + "="*70)
    print("📋 Available Sports Series:")
    print("="*70)
    for series in available_series[:20]:  # Show first 20
        print(f"  {series['ticker']:20s} - {series['title']}")

    # Analyze each sport
    print("\n" + "="*70)
    print("🔍 ANALYZING SPORTS")
    print("="*70)

    sport_results = []

    for sport_name, series_ticker in analyzer.sports_series.items():
        result = analyzer.analyze_sport(sport_name, series_ticker, target_matches=100)
        if result:
            sport_results.append(result)

    # Overall summary
    print("\n" + "="*70)
    print("📊 CROSS-SPORT COMPARISON")
    print("="*70)

    if sport_results:
        # Sort by accuracy
        sport_results_sorted = sorted(sport_results, key=lambda x: x['accuracy'], reverse=True)

        print(f"\n{'Sport':<25s} {'Crossed 90%':<15s} {'Accuracy':<12s} {'Avg Window'}")
        print("-"*70)

        for result in sport_results_sorted:
            sport = result['sport']
            crossed_pct = result['crossed_90'] / result['matches_analyzed'] * 100
            crossed_str = f"{result['crossed_90']}/{result['matches_analyzed']} ({crossed_pct:.0f}%)"
            accuracy_str = f"{result['accuracy']:.1f}%"
            window_str = f"{result['avg_betting_window']:.1f} min"

            print(f"{sport:<25s} {crossed_str:<15s} {accuracy_str:<12s} {window_str}")

        # Save detailed results
        output = {
            'analysis_date': datetime.utcnow().isoformat(),
            'sports_analyzed': len(sport_results),
            'sports': sport_results
        }

        with open('multi_sport_90_percent_analysis.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\n💾 Detailed results saved to: multi_sport_90_percent_analysis.json")

    print("="*70)

if __name__ == '__main__':
    main()
