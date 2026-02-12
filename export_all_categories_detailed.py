"""
Export ALL categories to event-level detailed CSV
Fetches detailed data from Kalshi API for every series across all 13 categories
"""

import requests
import json
import csv
from datetime import datetime
from typing import List, Dict, Tuple
import time

class ComprehensiveExporter:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.all_events = []
        self.events_crossed_90 = []

    def get_market_trades(self, ticker: str, max_trades: int = 1000) -> List[Tuple[str, int]]:
        """Get trades for a specific market"""
        url = f"{self.base_url}/markets/trades"
        params = {'ticker': ticker, 'limit': max_trades}

        try:
            response = requests.get(url, params=params, timeout=10)
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

    def analyze_90_crossing(self, trades: List[Tuple[str, int]]) -> Dict:
        """Analyze when price crossed 90%"""
        if not trades:
            return {'first_touch': None, 'permanent_crossing': None, 'ever_crossed': False}

        first_touch = None
        permanent_crossing = None
        last_below_90_idx = None

        for i, (timestamp, price) in enumerate(trades):
            if price >= 90 and first_touch is None:
                first_touch = {'timestamp': timestamp, 'price': price, 'index': i}
            if price < 90:
                last_below_90_idx = i

        if last_below_90_idx is not None:
            for i in range(last_below_90_idx + 1, len(trades)):
                if trades[i][1] >= 90:
                    permanent_crossing = {
                        'timestamp': trades[i][0],
                        'price': trades[i][1],
                        'index': i
                    }
                    break
        elif first_touch and first_touch['index'] == 0:
            permanent_crossing = first_touch

        return {
            'first_touch': first_touch,
            'permanent_crossing': permanent_crossing,
            'ever_crossed': first_touch is not None
        }

    def process_series(self, series_ticker: str, series_title: str, category: str, idx: int, total: int):
        """Process all settled markets for a series"""
        print(f"\n[{idx}/{total}] {category} - {series_ticker}")

        url = f"{self.base_url}/markets"
        params = {'series_ticker': series_ticker, 'limit': 200}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            markets_data = response.json()
            markets = markets_data.get('markets', [])

            # Filter for settled markets only
            settled_markets = [
                m for m in markets
                if m.get('result') and m.get('settlement_value') is not None
            ]

            print(f"  {len(settled_markets)} settled markets")

            for market in settled_markets:
                ticker = market.get('ticker')
                title = market.get('title', 'N/A')
                result = market.get('result', 'N/A')
                settlement_value = market.get('settlement_value')
                close_time = market.get('close_time', 'N/A')

                # Get trades
                trades = self.get_market_trades(ticker)

                # Analyze crossing
                crossing = self.analyze_90_crossing(trades)

                # Calculate betting window
                betting_window_min = None
                betting_window_sec = None

                if crossing['ever_crossed'] and crossing['permanent_crossing']:
                    try:
                        perm_cross_time = datetime.fromisoformat(crossing['permanent_crossing']['timestamp'].replace('Z', '+00:00'))
                        market_close_time = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                        time_diff = market_close_time - perm_cross_time
                        betting_window_sec = int(time_diff.total_seconds())
                        betting_window_min = round(betting_window_sec / 60, 1)
                    except:
                        pass

                # Determine if prediction was correct
                prediction_correct = ''
                if crossing['ever_crossed']:
                    prediction_correct = 'CORRECT' if settlement_value in [99, 100] else 'WRONG'

                event_data = {
                    'category': category,
                    'series_ticker': series_ticker,
                    'series_title': series_title,
                    'ticker': ticker,
                    'title': title,
                    'result': result,
                    'settlement': settlement_value,
                    'crossed_90': crossing['ever_crossed'],
                    'first_touch_time': crossing['first_touch']['timestamp'] if crossing['first_touch'] else '',
                    'first_touch_price': crossing['first_touch']['price'] if crossing['first_touch'] else '',
                    'perm_cross_time': crossing['permanent_crossing']['timestamp'] if crossing['permanent_crossing'] else '',
                    'perm_cross_price': crossing['permanent_crossing']['price'] if crossing['permanent_crossing'] else '',
                    'close_time': close_time,
                    'betting_window_min': betting_window_min if betting_window_min else '',
                    'betting_window_sec': betting_window_sec if betting_window_sec else '',
                    'prediction_correct': prediction_correct,
                    'trades_count': len(trades)
                }

                self.all_events.append(event_data)

                if crossing['ever_crossed']:
                    self.events_crossed_90.append(event_data)

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"  ❌ Error: {e}")

    def export_to_csv(self):
        """Export all events to CSV files"""
        print(f"\n{'='*70}")
        print(f"Total events processed: {len(self.all_events)}")
        print(f"Events that crossed 90%: {len(self.events_crossed_90)}")
        print(f"{'='*70}")

        # 1. ALL EVENTS - ALL CATEGORIES
        print("\n📊 Creating comprehensive_all_events_detailed.csv...")
        with open('comprehensive_all_events_detailed.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Category', 'Series Ticker', 'Series Title',
                'Ticker', 'Title', 'Result', 'Settlement (¢)',
                'Crossed 90%',
                'First Touch Time', 'First Touch Price (¢)',
                'Permanent Cross Time', 'Permanent Cross Price (¢)',
                'Market Close Time',
                'Betting Window (min)', 'Betting Window (sec)',
                'Prediction Correct', 'Trades Count'
            ])

            for event in self.all_events:
                writer.writerow([
                    event['category'], event['series_ticker'], event['series_title'],
                    event['ticker'], event['title'], event['result'], event['settlement'],
                    'YES' if event['crossed_90'] else 'NO',
                    event['first_touch_time'], event['first_touch_price'],
                    event['perm_cross_time'], event['perm_cross_price'],
                    event['close_time'],
                    event['betting_window_min'], event['betting_window_sec'],
                    event['prediction_correct'], event['trades_count']
                ])

        print(f"✅ Created comprehensive_all_events_detailed.csv ({len(self.all_events)} events)")

        # 2. ONLY EVENTS THAT CROSSED 90%
        print("\n📊 Creating comprehensive_crossed_90_detailed.csv...")
        with open('comprehensive_crossed_90_detailed.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Category', 'Series Ticker', 'Series Title',
                'Ticker', 'Title', 'Result', 'Settlement (¢)',
                'First Touch Time', 'First Touch Price (¢)',
                'Permanent Cross Time', 'Permanent Cross Price (¢)',
                'Market Close Time',
                'Betting Window (min)', 'Betting Window (sec)',
                'Prediction Correct', 'Trades Count'
            ])

            for event in self.events_crossed_90:
                writer.writerow([
                    event['category'], event['series_ticker'], event['series_title'],
                    event['ticker'], event['title'], event['result'], event['settlement'],
                    event['first_touch_time'], event['first_touch_price'],
                    event['perm_cross_time'], event['perm_cross_price'],
                    event['close_time'],
                    event['betting_window_min'], event['betting_window_sec'],
                    event['prediction_correct'], event['trades_count']
                ])

        print(f"✅ Created comprehensive_crossed_90_detailed.csv ({len(self.events_crossed_90)} events)")

        # 3. PER-CATEGORY FILES (for major categories)
        print("\n📊 Creating per-category CSV files...")

        by_category = {}
        for event in self.events_crossed_90:
            cat = event['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(event)

        for category, events in sorted(by_category.items()):
            if len(events) >= 5:  # Only if 5+ events
                filename = f"detailed_{category.lower().replace(' ', '_').replace('/', '_')}_crossed_90.csv"

                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Series Ticker', 'Series Title', 'Ticker', 'Title',
                        'Result', 'Settlement (¢)',
                        'First Touch Time', 'First Touch Price (¢)',
                        'Permanent Cross Time', 'Permanent Cross Price (¢)',
                        'Market Close Time',
                        'Betting Window (min)', 'Betting Window (sec)',
                        'Prediction Correct', 'Trades Count'
                    ])

                    for event in events:
                        writer.writerow([
                            event['series_ticker'], event['series_title'],
                            event['ticker'], event['title'],
                            event['result'], event['settlement'],
                            event['first_touch_time'], event['first_touch_price'],
                            event['perm_cross_time'], event['perm_cross_price'],
                            event['close_time'],
                            event['betting_window_min'], event['betting_window_sec'],
                            event['prediction_correct'], event['trades_count']
                        ])

                print(f"  ✅ {filename} ({len(events)} events)")


def main():
    print("="*70)
    print("📊 COMPREHENSIVE EVENT-LEVEL EXPORT - ALL CATEGORIES")
    print("="*70)

    # Load comprehensive analysis to get all series
    with open('comprehensive_kalshi_analysis.json', 'r') as f:
        data = json.load(f)

    series_list = data['series_results']
    print(f"\nProcessing {len(series_list)} series across all categories...")

    exporter = ComprehensiveExporter()

    for idx, series_info in enumerate(series_list, 1):
        exporter.process_series(
            series_info['series_ticker'],
            series_info['series_title'],
            series_info['category'],
            idx,
            len(series_list)
        )

    # Export everything to CSV
    exporter.export_to_csv()

    print("\n" + "="*70)
    print("✅ COMPREHENSIVE EXPORT COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
