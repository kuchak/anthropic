"""
Comprehensive Kalshi 90% Analysis - ALL Categories
Find the BEST market category for the 90% crossing strategy
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter

class ComprehensiveKalshiAnalyzer:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"

    def discover_all_series(self) -> Dict[str, List[Dict]]:
        """Discover ALL series on Kalshi, grouped by category"""
        print("🔍 Discovering all series on Kalshi...")

        url = f"{self.base_url}/series"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            all_series = data.get('series', [])
            print(f"✅ Found {len(all_series)} total series")

            # Group by category
            by_category = defaultdict(list)

            for series in all_series:
                category = series.get('category', 'Unknown')
                by_category[category].append({
                    'ticker': series.get('ticker'),
                    'title': series.get('title'),
                    'category': category
                })

            print(f"\n📊 Series by category:")
            for category, series_list in sorted(by_category.items()):
                print(f"  {category:30s}: {len(series_list):4d} series")

            return dict(by_category)

        except Exception as e:
            print(f"❌ Error discovering series: {e}")
            return {}

    def get_settled_markets(self, series_ticker: str, target_count: int = 500) -> List[Dict]:
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
            return all_settled if all_settled else []

    def get_match_id(self, ticker: str) -> str:
        """Extract match/event ID from ticker"""
        parts = ticker.rsplit('-', 1)
        return parts[0] if len(parts) > 1 else ticker

    def group_by_event(self, markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group markets by event (to avoid double-counting)"""
        events = defaultdict(list)

        for market in markets:
            event_id = self.get_match_id(market['ticker'])
            events[event_id].append(market)

        return dict(events)

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
                            max_hours_before_close: int = None) -> Optional[Dict]:
        """Find first touch of 90% at ANY point before close (no time restriction)"""
        if not close_time:
            return None

        close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))

        for timestamp, price in trades:
            try:
                trade_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                # No time restriction - find ANY 90% crossing before close
                if trade_dt <= close_dt and price >= 90:
                    return {
                        'timestamp': timestamp,
                        'price': price
                    }
            except:
                continue

        return None

    def analyze_event(self, event_id: str, markets: List[Dict]) -> Optional[Dict]:
        """Analyze a single event"""
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

        # Find 90% crossings (NO time restriction - anytime before close)
        crossing_a = self.find_first_90_touch(trades_a, close_time)
        crossing_b = self.find_first_90_touch(trades_b, close_time) if trades_b else None

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
            'event_id': event_id,
            'ticker': market['ticker'],
            'title': market.get('title', ''),
            'settlement_value': settlement,
            'first_touch': first_crossing,
            'betting_window_minutes': betting_window_minutes,
            'prediction_correct': correct
        }

    def analyze_series(self, series_info: Dict, target_events: int = 500) -> Optional[Dict]:
        """Analyze a single series"""
        series_ticker = series_info['ticker']
        series_title = series_info['title']

        # Get markets
        markets = self.get_settled_markets(series_ticker, target_count=target_events * 2)

        if len(markets) < 10:  # Skip if too few markets
            return None

        # Group by event
        events = self.group_by_event(markets)

        if len(events) < 10:  # Skip if too few events
            return None

        # Analyze events
        results = []
        event_items = list(events.items())[:target_events]

        for event_id, event_markets in event_items:
            result = self.analyze_event(event_id, event_markets)
            if result:
                results.append(result)

        if not results:
            return None

        # Calculate stats
        total_analyzed = min(target_events, len(events))
        crossed_90 = len(results)
        correct = len([r for r in results if r['prediction_correct']])
        accuracy = correct / crossed_90 * 100 if crossed_90 > 0 else 0

        # Betting windows
        windows = [r['betting_window_minutes'] for r in results if r['betting_window_minutes']]
        avg_window = sum(windows) / len(windows) if windows else 0

        return {
            'series_ticker': series_ticker,
            'series_title': series_title,
            'category': series_info['category'],
            'events_analyzed': total_analyzed,
            'crossed_90': crossed_90,
            'correct_predictions': correct,
            'accuracy': accuracy,
            'avg_betting_window': avg_window,
            'crossing_rate': crossed_90 / total_analyzed * 100 if total_analyzed > 0 else 0
        }

def main():
    analyzer = ComprehensiveKalshiAnalyzer()

    # Discover all series
    series_by_category = analyzer.discover_all_series()

    print("\n" + "="*70)
    print("🔍 ANALYZING ALL SERIES")
    print("="*70)

    all_results = []

    # Pre-filter: Check which series have enough markets
    print("\n🔍 Pre-filtering series with sufficient markets...")
    viable_series = []

    total_series = sum(len(series_list) for series_list in series_by_category.values())
    checked_count = 0

    for category, series_list in series_by_category.items():
        for series_info in series_list:
            checked_count += 1

            if checked_count % 100 == 0:
                print(f"  Checked: {checked_count}/{total_series} series...")

            # Quick check: does this series have at least 30 settled markets?
            markets = analyzer.get_settled_markets(series_info['ticker'], target_count=30)

            if len(markets) >= 30:
                viable_series.append(series_info)

    print(f"\n✅ Found {len(viable_series)} series with 50+ settled markets")

    # Now analyze viable series in detail (100 events for speed)
    print("\n" + "="*70)
    print("🔍 ANALYZING VIABLE SERIES (100 events each, NO TIME RESTRICTION)")
    print("="*70)

    analyzed_count = 0

    for series_info in viable_series:
        analyzed_count += 1

        if analyzed_count % 25 == 0:
            print(f"\n📊 Progress: {analyzed_count}/{len(viable_series)} series analyzed...")

        result = analyzer.analyze_series(series_info, target_events=100)

        if result:
            all_results.append(result)
            print(f"  ✅ Events: {result['events_analyzed']:3d} | "
                  f"Crossed: {result['crossing_rate']:5.1f}% | Accuracy: {result['accuracy']:5.1f}%")

    # Summary
    print("\n" + "="*70)
    print("📊 TOP PERFORMING SERIES BY ACCURACY")
    print("="*70)

    if all_results:
        # Filter for series with at least 50 events that crossed 90%
        significant_results = [r for r in all_results if r['crossed_90'] >= 50]

        # Sort by accuracy
        top_by_accuracy = sorted(significant_results, key=lambda x: x['accuracy'], reverse=True)[:30]

        print(f"\n{'Series':<30s} {'Category':<20s} {'Crossed':<10s} {'Accuracy':<10s} {'Window'}")
        print("-"*90)

        for result in top_by_accuracy:
            series_short = result['series_ticker'][:28]
            category_short = result['category'][:18]
            crossed_str = f"{result['crossed_90']}/{result['events_analyzed']}"
            accuracy_str = f"{result['accuracy']:.1f}%"
            window_str = f"{result['avg_betting_window']:.1f}m"

            print(f"{series_short:<30s} {category_short:<20s} {crossed_str:<10s} {accuracy_str:<10s} {window_str}")

        # Group by category
        print("\n" + "="*70)
        print("📊 TOP PERFORMING CATEGORIES")
        print("="*70)

        category_stats = defaultdict(list)

        for result in significant_results:
            category_stats[result['category']].append(result)

        category_summary = []

        for category, results in category_stats.items():
            total_crossed = sum(r['crossed_90'] for r in results)
            total_correct = sum(r['correct_predictions'] for r in results)
            avg_accuracy = total_correct / total_crossed * 100 if total_crossed > 0 else 0
            avg_window = sum(r['avg_betting_window'] for r in results) / len(results)

            category_summary.append({
                'category': category,
                'series_count': len(results),
                'total_crossed': total_crossed,
                'accuracy': avg_accuracy,
                'avg_window': avg_window
            })

        category_summary_sorted = sorted(category_summary, key=lambda x: x['accuracy'], reverse=True)

        print(f"\n{'Category':<30s} {'Series':<8s} {'Total Crossed':<15s} {'Accuracy':<12s} {'Avg Window'}")
        print("-"*90)

        for cat in category_summary_sorted[:20]:
            cat_name = cat['category'][:28]
            series_count = cat['series_count']
            crossed = cat['total_crossed']
            accuracy = f"{cat['accuracy']:.1f}%"
            window = f"{cat['avg_window']:.1f}m"

            print(f"{cat_name:<30s} {series_count:<8d} {crossed:<15d} {accuracy:<12s} {window}")

        # Save results
        output = {
            'analysis_date': datetime.utcnow().isoformat(),
            'total_series_analyzed': len(all_results),
            'series_results': all_results,
            'category_summary': category_summary
        }

        with open('comprehensive_kalshi_analysis.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\n💾 Detailed results saved to: comprehensive_kalshi_analysis.json")

    print("="*70)

if __name__ == '__main__':
    main()
