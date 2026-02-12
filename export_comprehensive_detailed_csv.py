"""
Export comprehensive analysis to event-level detailed CSV (tennis format)
Fetches trade data to get first touch, permanent crossing, betting windows, etc.
"""

import requests
import json
import csv
from datetime import datetime
from typing import List, Dict, Tuple

class ComprehensiveMarketAnalyzer:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"

    def get_market_trades(self, ticker: str, max_trades: int = 1000) -> List[Tuple[str, int]]:
        """Get trades for a specific market"""
        url = f"{self.base_url}/markets/trades"
        params = {
            'ticker': ticker,
            'limit': max_trades
        }

        try:
            response = requests.get(url, params=params, timeout=10)
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
            print(f"  ⚠️  Error fetching trades for {ticker}: {e}")
            return []

    def analyze_90_crossing(self, trades: List[Tuple[str, int]]) -> Dict:
        """Analyze when price crossed 90% and if it stayed there"""
        if not trades:
            return {
                'first_touch': None,
                'permanent_crossing': None,
                'ever_crossed': False
            }

        first_touch = None
        permanent_crossing = None
        last_below_90_idx = None

        # Find first touch of 90%
        for i, (timestamp, price) in enumerate(trades):
            if price >= 90 and first_touch is None:
                first_touch = {
                    'timestamp': timestamp,
                    'price': price,
                    'index': i
                }

            # Track last time it was below 90
            if price < 90:
                last_below_90_idx = i

        # Find permanent crossing
        if last_below_90_idx is not None:
            # Find next trade at/above 90 after the last sub-90 trade
            for i in range(last_below_90_idx + 1, len(trades)):
                if trades[i][1] >= 90:
                    permanent_crossing = {
                        'timestamp': trades[i][0],
                        'price': trades[i][1],
                        'index': i
                    }
                    break
        elif first_touch and first_touch['index'] == 0:
            # Started at/above 90% and never went below
            permanent_crossing = first_touch

        return {
            'first_touch': first_touch,
            'permanent_crossing': permanent_crossing,
            'ever_crossed': first_touch is not None
        }

def main():
    # Load the JSON with list of all events analyzed
    with open('comprehensive_kalshi_analysis.json', 'r') as f:
        data = json.load(f)

    print("="*70)
    print("📊 EXPORTING COMPREHENSIVE ANALYSIS TO DETAILED CSV")
    print("="*70)

    # We need to reload all markets to get individual event data
    # Let's fetch from the API
    base_url = "https://api.elections.kalshi.com/trade-api/v2"

    print("\n📥 Fetching all series data from API...")

    all_events = []
    events_crossed_90 = []

    analyzer = ComprehensiveMarketAnalyzer()

    # Get all series tickers from our analysis
    series_tickers = list(set(r['series_ticker'] for r in data['series_results']))

    print(f"Processing {len(series_tickers)} series...")

    for idx, series_ticker in enumerate(series_tickers, 1):
        print(f"\n[{idx}/{len(series_tickers)}] {series_ticker}")

        # Get series info
        series_info = next((r for r in data['series_results'] if r['series_ticker'] == series_ticker), None)
        if not series_info:
            continue

        category = series_info['category']
        series_title = series_info['series_title']

        # Fetch markets for this series
        url = f"{base_url}/markets"
        params = {
            'series_ticker': series_ticker,
            'limit': 200
        }

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

            print(f"  Found {len(settled_markets)} settled markets")

            # Analyze each market
            for market in settled_markets:
                ticker = market.get('ticker')
                title = market.get('title', 'N/A')
                result = market.get('result', 'N/A')
                settlement_value = market.get('settlement_value')
                close_time = market.get('close_time', 'N/A')

                # Get trades
                trades = analyzer.get_market_trades(ticker)

                if not trades:
                    # Add event without crossing data
                    all_events.append({
                        'category': category,
                        'series_ticker': series_ticker,
                        'series_title': series_title,
                        'ticker': ticker,
                        'title': title,
                        'result': result,
                        'settlement': settlement_value,
                        'crossed_90': False,
                        'close_time': close_time,
                        'trades_count': 0
                    })
                    continue

                # Analyze crossing
                crossing = analyzer.analyze_90_crossing(trades)

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

                all_events.append(event_data)

                if crossing['ever_crossed']:
                    events_crossed_90.append(event_data)

        except Exception as e:
            print(f"  ❌ Error processing {series_ticker}: {e}")
            continue

    print(f"\n{'='*70}")
    print(f"Total events processed: {len(all_events)}")
    print(f"Events that crossed 90%: {len(events_crossed_90)}")
    print(f"{'='*70}")

    # Export all events
    print("\n📊 Creating all_events_detailed.csv...")
    with open('all_events_detailed.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Category',
            'Series Ticker',
            'Series Title',
            'Ticker',
            'Title',
            'Result',
            'Settlement (¢)',
            'Crossed 90%',
            'First Touch Time',
            'First Touch Price (¢)',
            'Permanent Cross Time',
            'Permanent Cross Price (¢)',
            'Market Close Time',
            'Betting Window (min)',
            'Betting Window (sec)',
            'Prediction Correct',
            'Trades Count'
        ])

        for event in all_events:
            writer.writerow([
                event['category'],
                event['series_ticker'],
                event['series_title'],
                event['ticker'],
                event['title'],
                event['result'],
                event['settlement'],
                'YES' if event['crossed_90'] else 'NO',
                event.get('first_touch_time', ''),
                event.get('first_touch_price', ''),
                event.get('perm_cross_time', ''),
                event.get('perm_cross_price', ''),
                event['close_time'],
                event.get('betting_window_min', ''),
                event.get('betting_window_sec', ''),
                event.get('prediction_correct', ''),
                event['trades_count']
            ])

    print(f"✅ Created all_events_detailed.csv ({len(all_events)} events)")

    # Export events that crossed 90%
    print("\n📊 Creating events_crossed_90_detailed.csv...")
    with open('events_crossed_90_detailed.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Category',
            'Series Ticker',
            'Series Title',
            'Ticker',
            'Title',
            'Result',
            'Settlement (¢)',
            'First Touch Time',
            'First Touch Price (¢)',
            'Permanent Cross Time',
            'Permanent Cross Price (¢)',
            'Market Close Time',
            'Betting Window (min)',
            'Betting Window (sec)',
            'Prediction Correct',
            'Trades Count'
        ])

        for event in events_crossed_90:
            writer.writerow([
                event['category'],
                event['series_ticker'],
                event['series_title'],
                event['ticker'],
                event['title'],
                event['result'],
                event['settlement'],
                event['first_touch_time'],
                event['first_touch_price'],
                event['perm_cross_time'],
                event['perm_cross_price'],
                event['close_time'],
                event['betting_window_min'],
                event['betting_window_sec'],
                event['prediction_correct'],
                event['trades_count']
            ])

    print(f"✅ Created events_crossed_90_detailed.csv ({len(events_crossed_90)} events)")

    print("\n" + "="*70)
    print("✅ EXPORT COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()
