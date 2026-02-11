"""
Check when Tiafoe odds crossed 90% on Kalshi and Polymarket
Specific market: Tiafoe vs Atmane - Feb 9, 2026
"""

import requests
import json
from datetime import datetime
from typing import Optional, Tuple, List

class MarketChecker:
    def __init__(self):
        self.kalshi_base = "https://api.elections.kalshi.com/trade-api/v2"
        self.polymarket_base = "https://clob.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"

    def check_kalshi_market(self, series_ticker: str, market_ticker: str) -> dict:
        """Check Kalshi market for 90% crossing"""
        print(f"\n{'='*70}")
        print(f"🔍 KALSHI: Checking market {market_ticker}")
        print(f"{'='*70}")

        # Get market info
        market_url = f"{self.kalshi_base}/markets/{market_ticker}"
        try:
            response = requests.get(market_url)
            response.raise_for_status()
            market_data = response.json()

            if 'market' in market_data:
                market = market_data['market']
                print(f"📊 Market: {market.get('title', 'N/A')}")
                print(f"📅 Status: {market.get('status', 'N/A')}")
                print(f"🎯 Result: {market.get('result', 'N/A')}")
                print(f"💰 Volume: ${market.get('volume', 0):,}")
                print(f"💵 Last Price: {market.get('last_price', 'N/A')}¢")
        except Exception as e:
            print(f"❌ Error getting market info: {e}")
            return {'error': str(e)}

        # Get candlestick data (1-minute intervals for precision)
        print(f"\n📈 Fetching candlestick data (1-minute intervals)...")
        candle_url = f"{self.kalshi_base}/series/{series_ticker}/markets/{market_ticker}/candlesticks"

        results = []
        for interval in [1, 60, 1440]:  # 1min, 1hr, 1day
            try:
                params = {'period_interval': interval}
                response = requests.get(candle_url, params=params)
                response.raise_for_status()
                data = response.json()

                if 'candlesticks' in data and data['candlesticks']:
                    candles = sorted(data['candlesticks'], key=lambda x: x.get('end_period_ts', 0))

                    # Find first 90% crossing
                    prev_price = None
                    for candle in candles:
                        if 'price' in candle and 'close' in candle['price']:
                            curr_price = candle['price']['close']
                            timestamp = candle.get('end_period_ts')

                            if prev_price is not None and prev_price < 90 and curr_price >= 90:
                                dt = datetime.fromtimestamp(timestamp)
                                results.append({
                                    'interval': f"{interval}min",
                                    'timestamp': timestamp,
                                    'datetime': dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                                    'price': curr_price,
                                    'prev_price': prev_price
                                })
                                break
                            prev_price = curr_price

                    print(f"✅ Got {len(candles)} candles for {interval}min interval")
                else:
                    print(f"⚠️  No candlestick data for {interval}min interval")

            except Exception as e:
                print(f"⚠️  Error with {interval}min interval: {e}")

        return {
            'market_data': market_data.get('market', {}),
            'crossings': results
        }

    def check_polymarket_market(self, market_url: str) -> dict:
        """Check Polymarket market for 90% crossing"""
        print(f"\n{'='*70}")
        print(f"🔍 POLYMARKET: Checking market")
        print(f"{'='*70}")

        # Extract slug from URL
        slug = market_url.split('/')[-1]
        print(f"📌 Market slug: {slug}")

        # Try to find market by searching
        try:
            # Method 1: Try Gamma API for market search
            search_url = f"{self.gamma_api}/markets"
            params = {'slug': slug}
            response = requests.get(search_url, params=params)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found market data via Gamma API")

                if isinstance(data, list) and len(data) > 0:
                    market = data[0]
                    print(f"📊 Market: {market.get('question', 'N/A')}")
                    print(f"📅 Active: {market.get('active', 'N/A')}")
                    print(f"🎯 Closed: {market.get('closed', 'N/A')}")

                    # Get condition_id/token_id for price history
                    condition_id = market.get('condition_id')
                    tokens = market.get('tokens', [])

                    if tokens:
                        print(f"\n🎲 Outcomes:")
                        for token in tokens:
                            print(f"   • {token.get('outcome', 'N/A')}: {token.get('token_id', 'N/A')}")

                    # Try to get price history
                    return self._get_polymarket_price_history(market, slug)
            else:
                print(f"⚠️  Gamma API returned status {response.status_code}")

        except Exception as e:
            print(f"⚠️  Error with Gamma API: {e}")

        # Method 2: Try CLOB API
        try:
            print(f"\n🔄 Trying CLOB API...")
            clob_url = f"{self.polymarket_base}/markets/{slug}"
            response = requests.get(clob_url)

            if response.status_code == 200:
                print(f"✅ Got data from CLOB API")
                data = response.json()
                return {'market_data': data, 'source': 'clob'}
        except Exception as e:
            print(f"⚠️  Error with CLOB API: {e}")

        return {'error': 'Could not fetch Polymarket data'}

    def _get_polymarket_price_history(self, market: dict, slug: str) -> dict:
        """Get price history from Polymarket"""
        print(f"\n📈 Fetching price history...")

        # Try to get events/price data
        condition_id = market.get('condition_id')
        tokens = market.get('tokens', [])

        results = []

        # Look for Tiafoe outcome
        tiafoe_token = None
        for token in tokens:
            outcome = token.get('outcome', '').lower()
            if 'tiafoe' in outcome:
                tiafoe_token = token
                print(f"✅ Found Tiafoe token: {token.get('token_id')}")
                break

        if tiafoe_token:
            token_id = tiafoe_token.get('token_id')

            # Try to get price snapshots/trades
            try:
                # Gamma API for price history
                price_url = f"{self.gamma_api}/prices"
                params = {
                    'market': condition_id,
                }
                response = requests.get(price_url, params=params)

                if response.status_code == 200:
                    price_data = response.json()
                    print(f"✅ Got price history data")

                    # Analyze for 90% crossing
                    if 'history' in price_data:
                        prev_price = None
                        for point in sorted(price_data['history'], key=lambda x: x.get('t', 0)):
                            curr_price = point.get('p', 0) * 100  # Convert to cents
                            timestamp = point.get('t', 0)

                            if prev_price is not None and prev_price < 90 and curr_price >= 90:
                                dt = datetime.fromtimestamp(timestamp)
                                results.append({
                                    'timestamp': timestamp,
                                    'datetime': dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                                    'price': curr_price,
                                    'prev_price': prev_price
                                })
                                break
                            prev_price = curr_price

            except Exception as e:
                print(f"⚠️  Error getting price history: {e}")

        return {
            'market_data': market,
            'crossings': results
        }


def main():
    # Market details
    kalshi_series = "KXATPMATCH"
    kalshi_market = "KXATPMATCH-26FEB09ATMTIA"
    polymarket_url = "https://polymarket.com/sports/atp/atp-atmane-tiafoe-2026-02-09"

    checker = MarketChecker()

    print(f"{'='*70}")
    print(f"🎾 ATP TENNIS: Tiafoe vs Atmane - February 9, 2026")
    print(f"   Checking when Tiafoe odds crossed 90% on each platform")
    print(f"{'='*70}")

    # Check Kalshi
    kalshi_result = checker.check_kalshi_market(kalshi_series, kalshi_market)

    # Check Polymarket
    polymarket_result = checker.check_polymarket_market(polymarket_url)

    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")

    print(f"\n🏆 KALSHI:")
    if 'crossings' in kalshi_result and kalshi_result['crossings']:
        for crossing in kalshi_result['crossings']:
            print(f"   ✅ Crossed 90% at: {crossing['datetime']}")
            print(f"      Price: {crossing['prev_price']}¢ → {crossing['price']}¢")
            print(f"      Interval: {crossing['interval']}")
    else:
        print(f"   ❌ No 90% crossing detected in candlestick data")
        if 'market_data' in kalshi_result:
            last_price = kalshi_result['market_data'].get('last_price', 'N/A')
            print(f"   💵 Final price: {last_price}¢")

    print(f"\n🎲 POLYMARKET:")
    if 'crossings' in polymarket_result and polymarket_result['crossings']:
        for crossing in polymarket_result['crossings']:
            print(f"   ✅ Crossed 90% at: {crossing['datetime']}")
            print(f"      Price: {crossing['prev_price']}¢ → {crossing['price']}¢")
    else:
        print(f"   ❌ No 90% crossing detected or data unavailable")

    # Save raw data
    output = {
        'kalshi': kalshi_result,
        'polymarket': polymarket_result
    }

    with open('tiafoe_atmane_90_check.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Raw data saved to: tiafoe_atmane_90_check.json")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
