"""
Kalshi Market Backtesting Script - Production Version
Analyzes the accuracy of markets at their FIRST 90% crossing
Includes robust rate limiting and filters for end-game convergence

Key Features:
- Tracks FIRST crossing of 90% threshold (even if it jumps from 89% to 93%)
- Configurable rate limiting to avoid API bans
- Batch processing with pauses
- Exponential backoff on errors
- Category-based analysis
- CSV export with detailed timestamps
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from collections import defaultdict
import sys


class KalshiBacktester:
    def __init__(self, rate_limit_delay: float = 1.0, batch_size: int = 50, batch_pause: int = 30):
        """
        Initialize the backtester with configurable rate limiting

        Args:
            rate_limit_delay: Seconds to wait between API calls (default: 1.0)
            batch_size: Number of markets to process before pausing (default: 50)
            batch_pause: Seconds to pause after each batch (default: 30)
        """
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay
        self.batch_size = batch_size
        self.batch_pause = batch_pause
        self.request_count = 0

    def _rate_limit(self):
        """Apply rate limiting delay"""
        time.sleep(self.rate_limit_delay)
        self.request_count += 1

    def _batch_pause_check(self, current_index: int):
        """Check if we need to pause after processing a batch"""
        if current_index > 0 and current_index % self.batch_size == 0:
            print(f"\n⏸️  Processed {current_index} markets, pausing for {self.batch_pause}s to respect rate limits...")
            time.sleep(self.batch_pause)

    def _make_request(self, url: str, params: Optional[Dict] = None, retries: int = 3) -> Optional[Dict]:
        """
        Make API request with exponential backoff on rate limit errors

        Args:
            url: API endpoint URL
            params: Query parameters
            retries: Number of retry attempts

        Returns:
            JSON response or None on failure
        """
        for attempt in range(retries):
            try:
                self._rate_limit()
                response = self.session.get(url, params=params)

                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = 60 * (2 ** attempt)  # Exponential backoff: 60s, 120s, 240s
                    print(f"\n⚠️  Rate limited! Waiting {wait_time}s before retry (attempt {attempt + 1}/{retries})...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e}")
                if attempt == retries - 1:
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Request Error: {e}")
                if attempt == retries - 1:
                    return None

        return None

    def get_settled_markets(self, limit: int = 1000, cursor: Optional[str] = None) -> Optional[Dict]:
        """Fetch settled markets from Kalshi API"""
        url = f"{self.base_url}/markets"
        params = {
            'status': 'settled',
            'limit': limit
        }
        if cursor:
            params['cursor'] = cursor

        return self._make_request(url, params)

    def get_market_candlesticks(self, series_ticker: str, market_ticker: str,
                                start_ts: Optional[int] = None,
                                end_ts: Optional[int] = None,
                                period_interval: int = 1440) -> Optional[Dict]:
        """
        Fetch candlestick data for a market
        period_interval: 1 (1 min), 60 (1 hour), 1440 (1 day)
        """
        url = f"{self.base_url}/series/{series_ticker}/markets/{market_ticker}/candlesticks"
        params = {
            'period_interval': period_interval
        }
        if start_ts:
            params['start_ts'] = start_ts
        if end_ts:
            params['end_ts'] = end_ts

        return self._make_request(url, params)

    def get_series_info(self, series_ticker: str) -> Optional[Dict]:
        """Get series information including category"""
        url = f"{self.base_url}/series/{series_ticker}"
        return self._make_request(url)

    def find_first_90_crossing(self, candlestick_data: Dict, threshold: int = 90) -> Optional[Tuple[int, Dict]]:
        """
        Find the FIRST time a market crossed the 90% threshold
        Handles cases where market jumps from 89% to 93% (still captures the crossing)

        Args:
            candlestick_data: Candlestick data from API
            threshold: Threshold in cents (default: 90 = 90%)

        Returns:
            Tuple of (timestamp, candle_data) or None if never crossed
        """
        if not candlestick_data or 'candlesticks' not in candlestick_data:
            return None

        candles = candlestick_data['candlesticks']
        if not candles:
            return None

        # Sort by timestamp to ensure chronological order
        sorted_candles = sorted(candles, key=lambda x: x.get('end_period_ts', 0))

        previous_price = None

        for candle in sorted_candles:
            # Get current close price
            current_price = None
            if 'price' in candle and 'close' in candle['price']:
                current_price = candle['price']['close']

            if current_price is None:
                continue

            # Check if we crossed from below threshold to at-or-above threshold
            if previous_price is not None:
                if previous_price < threshold and current_price >= threshold:
                    # Found the first crossing!
                    return (candle.get('end_period_ts'), candle)

            previous_price = current_price

        # Check if market started above 90% (edge case)
        if sorted_candles and 'price' in sorted_candles[0] and 'close' in sorted_candles[0]['price']:
            first_price = sorted_candles[0]['price']['close']
            if first_price >= threshold:
                # Market opened at or above 90%
                return (sorted_candles[0].get('end_period_ts'), sorted_candles[0])

        return None

    def calculate_timing_metrics(self, crossing_ts: int, market_open_ts: int, market_close_ts: int) -> Dict:
        """
        Calculate when the 90% crossing happened relative to market lifetime

        Returns:
            Dict with timing metrics
        """
        total_duration = market_close_ts - market_open_ts
        time_to_crossing = crossing_ts - market_open_ts
        time_after_crossing = market_close_ts - crossing_ts

        # Percentage of market lifetime when it crossed 90%
        crossing_pct = (time_to_crossing / total_duration * 100) if total_duration > 0 else 0

        return {
            'total_duration_hours': total_duration / 3600,
            'time_to_crossing_hours': time_to_crossing / 3600,
            'time_after_crossing_hours': time_after_crossing / 3600,
            'crossing_at_pct_of_lifetime': crossing_pct
        }

    def analyze_markets(self, max_markets: int = 200, threshold: int = 90,
                       period_interval: int = 1440) -> Tuple[pd.DataFrame, Dict]:
        """
        Main analysis function
        Fetches settled markets and analyzes first 90% crossing accuracy

        Args:
            max_markets: Maximum number of markets to analyze
            threshold: Probability threshold in % (default: 90)
            period_interval: Candlestick interval - 1 (1min), 60 (1hr), 1440 (1day)
        """
        print(f"🚀 Starting Kalshi backtesting analysis...")
        print(f"📊 Threshold: {threshold}% probability")
        print(f"⏱️  Rate limit: {self.rate_limit_delay}s between requests")
        print(f"📦 Batch size: {self.batch_size} markets (pause {self.batch_pause}s between batches)")
        print(f"🕐 Candlestick interval: {period_interval} minutes")
        print("=" * 70)

        all_markets = []
        cursor = None
        markets_fetched = 0

        # Fetch settled markets
        print(f"\n📥 Fetching settled markets from Kalshi API...")
        while markets_fetched < max_markets:
            print(f"   Fetched: {markets_fetched}/{max_markets}", end='\r')
            data = self.get_settled_markets(limit=1000, cursor=cursor)

            if not data or 'markets' not in data or len(data['markets']) == 0:
                break

            all_markets.extend(data['markets'])
            markets_fetched += len(data['markets'])

            # Check if there's more data
            cursor = data.get('cursor')
            if not cursor:
                break

        print(f"\n✅ Total settled markets found: {len(all_markets)}")

        # Analyze each market
        results = []
        category_stats = defaultdict(lambda: {
            'total_hit_90': 0,
            'correct_predictions': 0,
            'early_signals': 0,  # Crossed in first 50% of market life
            'late_signals': 0    # Crossed in last 50% of market life
        })

        markets_to_analyze = min(max_markets, len(all_markets))
        print(f"\n🔍 Analyzing {markets_to_analyze} markets for first 90% crossings...")
        print("=" * 70)

        for i, market in enumerate(all_markets[:markets_to_analyze]):
            # Progress indicator
            if (i + 1) % 10 == 0:
                progress = (i + 1) / markets_to_analyze * 100
                print(f"Progress: {i+1}/{markets_to_analyze} ({progress:.1f}%)")

            # Batch pause check
            self._batch_pause_check(i + 1)

            ticker = market['ticker']

            # Extract series ticker from market ticker
            series_ticker = ticker.split('-')[0] if '-' in ticker else ticker

            # Get series info for category
            series_info = self.get_series_info(series_ticker)
            category = 'Unknown'
            if series_info and 'series' in series_info:
                category = series_info['series'].get('category', 'Unknown')

            # Get candlestick data
            candlesticks = self.get_market_candlesticks(
                series_ticker,
                ticker,
                period_interval=period_interval
            )

            # Find first 90% crossing
            crossing_result = self.find_first_90_crossing(candlesticks, threshold)

            # Parse timestamps
            open_ts = self._parse_timestamp(market.get('open_time'))
            close_ts = self._parse_timestamp(market.get('close_time'))

            # Calculate timing metrics if we found a crossing
            timing_metrics = None
            if crossing_result and open_ts and close_ts:
                crossing_ts, crossing_candle = crossing_result
                timing_metrics = self.calculate_timing_metrics(crossing_ts, open_ts, close_ts)

            # Get actual result
            result = market.get('result')  # 'yes' or 'no'

            # Determine if crossing was early or late
            signal_timing = None
            if timing_metrics:
                if timing_metrics['crossing_at_pct_of_lifetime'] < 50:
                    signal_timing = 'early'
                else:
                    signal_timing = 'late'

            # Store result
            market_data = {
                'ticker': ticker,
                'title': market.get('title', ''),
                'category': category,
                'series_ticker': series_ticker,
                'result': result,
                'hit_90_percent': crossing_result is not None,
                'crossing_timestamp': crossing_result[0] if crossing_result else None,
                'crossing_price': crossing_result[1]['price']['close'] if crossing_result and 'price' in crossing_result[1] else None,
                'volume': market.get('volume', 0),
                'signal_timing': signal_timing,
            }

            # Add timing metrics
            if timing_metrics:
                market_data.update({
                    'total_duration_hours': timing_metrics['total_duration_hours'],
                    'time_to_crossing_hours': timing_metrics['time_to_crossing_hours'],
                    'time_after_crossing_hours': timing_metrics['time_after_crossing_hours'],
                    'crossing_at_pct_of_lifetime': timing_metrics['crossing_at_pct_of_lifetime']
                })

            results.append(market_data)

            # Update category stats
            if crossing_result:
                category_stats[category]['total_hit_90'] += 1

                # Check if the 90% prediction was correct
                if result == 'yes':
                    category_stats[category]['correct_predictions'] += 1

                # Track early vs late signals
                if signal_timing == 'early':
                    category_stats[category]['early_signals'] += 1
                elif signal_timing == 'late':
                    category_stats[category]['late_signals'] += 1

        # Create DataFrame
        df = pd.DataFrame(results)

        # Calculate and display statistics
        self._display_results(df, category_stats, threshold)

        # Save results to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kalshi_backtest_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"\n💾 Detailed results saved to: {filename}")

        return df, category_stats

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[int]:
        """Parse ISO timestamp string to Unix timestamp"""
        if not timestamp_str:
            return None
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except:
            return None

    def _display_results(self, df: pd.DataFrame, category_stats: Dict, threshold: int):
        """Display analysis results"""
        markets_that_hit_90 = df[df['hit_90_percent'] == True]
        total_90_markets = len(markets_that_hit_90)

        print("\n" + "=" * 70)
        print("📈 OVERALL RESULTS")
        print("=" * 70)
        print(f"Total markets analyzed: {len(df)}")
        print(f"Markets that crossed {threshold}%: {total_90_markets}")

        if total_90_markets > 0:
            correct_90_markets = len(markets_that_hit_90[markets_that_hit_90['result'] == 'yes'])
            accuracy = (correct_90_markets / total_90_markets) * 100

            print(f"Correct predictions (resolved YES): {correct_90_markets}")
            print(f"⭐ Overall Accuracy: {accuracy:.2f}%")

            # Early vs Late signal analysis
            early_signals = markets_that_hit_90[markets_that_hit_90['signal_timing'] == 'early']
            late_signals = markets_that_hit_90[markets_that_hit_90['signal_timing'] == 'late']

            if len(early_signals) > 0:
                early_accuracy = len(early_signals[early_signals['result'] == 'yes']) / len(early_signals) * 100
                print(f"\n🔹 Early signals (first 50% of market life): {len(early_signals)} markets, {early_accuracy:.2f}% accurate")

            if len(late_signals) > 0:
                late_accuracy = len(late_signals[late_signals['result'] == 'yes']) / len(late_signals) * 100
                print(f"🔸 Late signals (last 50% of market life): {len(late_signals)} markets, {late_accuracy:.2f}% accurate")

            # Category breakdown
            print("\n" + "=" * 70)
            print("📊 ACCURACY BY CATEGORY")
            print("=" * 70)

            category_results = []
            for category, stats in category_stats.items():
                if stats['total_hit_90'] > 0:
                    cat_accuracy = (stats['correct_predictions'] / stats['total_hit_90']) * 100
                    category_results.append({
                        'Category': category,
                        'Hit 90%': stats['total_hit_90'],
                        'Correct': stats['correct_predictions'],
                        'Accuracy': f"{cat_accuracy:.1f}%",
                        'Early': stats['early_signals'],
                        'Late': stats['late_signals']
                    })

            cat_df = pd.DataFrame(category_results)
            cat_df = cat_df.sort_values('Hit 90%', ascending=False)
            print(cat_df.to_string(index=False))

        else:
            print(f"\n⚠️  No markets crossed the {threshold}% threshold in the dataset.")
            print("Try lowering the threshold (e.g., 85%) or analyzing more markets.")


def main():
    """Main execution function"""

    # Configuration
    MAX_MARKETS = 200          # Number of markets to analyze
    THRESHOLD = 90             # Probability threshold (90 = 90%)
    RATE_LIMIT_DELAY = 1.0     # Seconds between API calls (1.0 = conservative)
    BATCH_SIZE = 50            # Process this many markets before pausing
    BATCH_PAUSE = 30           # Pause duration in seconds
    PERIOD_INTERVAL = 1440     # Candlestick interval: 1 (1min), 60 (1hr), 1440 (1day)

    print("=" * 70)
    print("🎯 KALSHI MARKET BACKTESTING TOOL")
    print("=" * 70)
    print("\nConfiguration:")
    print(f"  • Markets to analyze: {MAX_MARKETS}")
    print(f"  • Threshold: {THRESHOLD}%")
    print(f"  • Rate limit: {RATE_LIMIT_DELAY}s per request")
    print(f"  • Batch processing: {BATCH_SIZE} markets, {BATCH_PAUSE}s pause")
    print(f"  • Candlestick interval: {PERIOD_INTERVAL} minutes")
    print("=" * 70)

    # Create backtester with conservative rate limiting
    backtester = KalshiBacktester(
        rate_limit_delay=RATE_LIMIT_DELAY,
        batch_size=BATCH_SIZE,
        batch_pause=BATCH_PAUSE
    )

    # Run analysis
    try:
        results_df, category_stats = backtester.analyze_markets(
            max_markets=MAX_MARKETS,
            threshold=THRESHOLD,
            period_interval=PERIOD_INTERVAL
        )

        print("\n" + "=" * 70)
        print("✅ Analysis complete!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
