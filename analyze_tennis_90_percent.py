"""
Analyze recent settled tennis markets on Kalshi for 90% crossing accuracy
Find first touch and permanent crossing of 90% and verify settlement
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class TennisMarketAnalyzer:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.tennis_series = "KXATPMATCH"

    def get_settled_tennis_markets(self, limit: int = 50) -> List[Dict]:
        """Get recent settled tennis markets"""
        print(f"📊 Fetching tennis markets from Kalshi...")

        url = f"{self.base_url}/markets"
        params = {
            'series_ticker': self.tennis_series,
            'limit': 200  # Get more to ensure we have enough settled ones
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            all_markets = data.get('markets', [])
            print(f"📥 Retrieved {len(all_markets)} total markets")

            # Filter for settled markets (has result and settlement_value)
            settled_markets = [
                m for m in all_markets
                if m.get('result') and m.get('settlement_value') is not None
            ]

            print(f"✅ Found {len(settled_markets)} settled tennis markets")

            # Sort by close time (most recent first)
            markets_sorted = sorted(
                settled_markets,
                key=lambda x: x.get('close_time', ''),
                reverse=True
            )

            return markets_sorted[:limit]

        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []

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

    def analyze_90_crossing(self, trades: List[Tuple[str, int]]) -> Dict:
        """Analyze when price crossed 90% and if it stayed there"""
        if not trades:
            return {
                'first_touch': None,
                'permanent_crossing': None,
                'ever_crossed': False,
                'stayed_above': False
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
                        'index': i,
                        'last_below_90': {
                            'timestamp': trades[last_below_90_idx][0],
                            'price': trades[last_below_90_idx][1]
                        }
                    }
                    break
        elif first_touch and first_touch['index'] == 0:
            # Started at/above 90% and never went below
            permanent_crossing = first_touch

        # Check if it stayed above 90% after permanent crossing
        stayed_above = False
        if permanent_crossing:
            stayed_above = all(
                price >= 90
                for _, price in trades[permanent_crossing['index']:]
            )

        return {
            'first_touch': first_touch,
            'permanent_crossing': permanent_crossing,
            'ever_crossed': first_touch is not None,
            'stayed_above': stayed_above,
            'total_trades': len(trades)
        }

    def analyze_market(self, market: Dict) -> Dict:
        """Analyze a single market for 90% crossing accuracy"""
        ticker = market.get('ticker')
        title = market.get('title', 'N/A')
        result = market.get('result', 'N/A')
        settlement_value = market.get('settlement_value')
        close_time = market.get('close_time', 'N/A')

        print(f"\n{'='*70}")
        print(f"📈 {ticker}")
        print(f"   {title}")
        print(f"   Closed: {close_time}")
        print(f"   Result: {result} | Settlement: {settlement_value}¢")

        # Get trades
        trades = self.get_market_trades(ticker)
        print(f"   Trades: {len(trades)}")

        if not trades:
            return {
                'ticker': ticker,
                'title': title,
                'result': result,
                'settlement_value': settlement_value,
                'error': 'No trade data available'
            }

        # Analyze 90% crossing
        crossing = self.analyze_90_crossing(trades)

        # Report findings
        if crossing['ever_crossed']:
            first_touch = crossing['first_touch']
            perm_cross = crossing['permanent_crossing']

            print(f"\n   ✅ CROSSED 90%:")
            print(f"      First touch: {first_touch['timestamp']} at {first_touch['price']}¢")

            if perm_cross:
                print(f"      Permanent:   {perm_cross['timestamp']} at {perm_cross['price']}¢")
                if crossing['stayed_above']:
                    print(f"      ✓ Stayed above 90% after permanent crossing")
                else:
                    print(f"      ✗ Did NOT stay above 90%")

            # Check if settlement matches 90%+ prediction
            correct_prediction = settlement_value in [99, 100] if settlement_value else False

            if correct_prediction:
                print(f"\n   🎯 PREDICTION CORRECT: Settled at {settlement_value}¢")
            else:
                print(f"\n   ❌ PREDICTION WRONG: Settled at {settlement_value}¢ (not 99-100)")

        else:
            print(f"   ⚪ Never crossed 90%")

        return {
            'ticker': ticker,
            'title': title,
            'result': result,
            'settlement_value': settlement_value,
            'close_time': close_time,
            'trades_count': len(trades),
            'crossed_90': crossing['ever_crossed'],
            'first_touch': crossing['first_touch'],
            'permanent_crossing': crossing['permanent_crossing'],
            'stayed_above_90': crossing['stayed_above'],
            'settled_99_100': settlement_value in [99, 100] if settlement_value else False
        }


def main():
    analyzer = TennisMarketAnalyzer()

    print("="*70)
    print("🎾 KALSHI TENNIS MARKETS: 90% CROSSING ACCURACY ANALYSIS")
    print("="*70)

    # Get settled markets
    markets = analyzer.get_settled_tennis_markets(limit=100)

    if not markets:
        print("❌ No markets found")
        return

    # Analyze the 10 most recent
    results = []
    for i, market in enumerate(markets[:10]):
        print(f"\n[{i+1}/10]", end=" ")
        result = analyzer.analyze_market(market)
        results.append(result)

    # Summary statistics
    print("\n" + "="*70)
    print("📊 SUMMARY STATISTICS")
    print("="*70)

    markets_crossed_90 = [r for r in results if r.get('crossed_90')]
    markets_settled_99_100 = [r for r in results if r.get('settled_99_100')]

    # Of markets that crossed 90%, how many settled at 99-100?
    if markets_crossed_90:
        correct_predictions = [
            r for r in markets_crossed_90
            if r.get('settled_99_100')
        ]
        accuracy = len(correct_predictions) / len(markets_crossed_90) * 100

        print(f"\n📈 Markets that crossed 90%: {len(markets_crossed_90)}/10")
        print(f"🎯 Settled at 99-100¢: {len(correct_predictions)}/{len(markets_crossed_90)}")
        print(f"📊 Accuracy: {accuracy:.1f}%")

        if correct_predictions != markets_crossed_90:
            print(f"\n⚠️  False positives (crossed 90% but didn't settle 99-100):")
            for r in markets_crossed_90:
                if not r.get('settled_99_100'):
                    print(f"   - {r['ticker']}: Settled at {r['settlement_value']}¢")
    else:
        print("\n⚪ None of the analyzed markets crossed 90%")

    # Detailed results table
    print("\n" + "="*70)
    print("📋 DETAILED RESULTS")
    print("="*70)

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['ticker']}")
        print(f"   Settlement: {r['settlement_value']}¢ | Result: {r['result']}")

        if r.get('crossed_90'):
            ft = r['first_touch']
            pc = r['permanent_crossing']

            print(f"   First 90%:  {ft['timestamp']} ({ft['price']}¢)")
            if pc:
                print(f"   Permanent:  {pc['timestamp']} ({pc['price']}¢)")

            status = "✅ CORRECT" if r.get('settled_99_100') else "❌ WRONG"
            print(f"   Prediction: {status}")
        else:
            print(f"   90% cross:  Never crossed")

    # Save results
    output = {
        'analysis_date': datetime.utcnow().isoformat(),
        'total_analyzed': len(results),
        'crossed_90_count': len(markets_crossed_90),
        'accuracy': accuracy if markets_crossed_90 else 0,
        'markets': results
    }

    with open('tennis_90_accuracy_analysis.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to: tennis_90_accuracy_analysis.json")
    print("="*70)


if __name__ == "__main__":
    main()
