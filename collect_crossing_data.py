"""
Collect 90¢ crossing data from Kalshi API

For each settled market in the past 30 days:
- Fetch full price history
- Detect every time price crossed above 90¢
- Record if/when it dropped back below
- Record final outcome

Output: CSV with one row per crossing (not per market)
"""
import os
import sys
import yaml
import csv
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dateutil.parser import parse as parse_datetime

# Add kalshi-bot to path
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')
from kalshi_client import KalshiClient


def get_top_volume_series(client: KalshiClient, limit: int = 5) -> List[str]:
    """
    Get the top series tickers by market volume

    Returns:
        List of series ticker strings
    """
    # Start with our known profitable tickers
    # These are high-volume from our backtest
    top_series = [
        'KXNBAGAME',    # NBA - very high volume
        'KXNHLGAME',    # NHL - high volume
        'KXATPMATCH',   # Tennis ATP - high volume
        'KXEPLGAME',    # Soccer EPL - high volume
        'KXBTC15M',     # Bitcoin - high frequency
    ]
    return top_series[:limit]


def get_settled_markets(
    client: KalshiClient,
    series_ticker: str,
    days_back: int = 30
) -> List[Dict]:
    """
    Get all settled markets for a series in the past N days

    Args:
        client: KalshiClient instance
        series_ticker: Series ticker to query
        days_back: How many days back to search

    Returns:
        List of market dicts
    """
    print(f"  Fetching settled markets for {series_ticker}...")

    markets = client.get_markets(
        category=series_ticker,
        status='settled',
        limit=1000
    )

    # Filter by settlement date
    from datetime import timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent_markets = []

    for m in markets:
        close_time = parse_datetime(m.get('close_time'))
        if close_time >= cutoff_date:
            recent_markets.append(m)

    print(f"    Found {len(recent_markets)} markets settled in past {days_back} days")
    return recent_markets


def get_price_history(client: KalshiClient, ticker: str) -> List[Dict]:
    """
    Get price history for a market

    Uses the /markets/{ticker}/history endpoint

    Returns:
        List of price data points sorted by timestamp
    """
    try:
        # Try to get candlestick/trade history
        # The endpoint might be /markets/{ticker}/history or /markets/{ticker}/trades
        response = client._request('GET', f'/markets/{ticker}/history')

        if 'history' in response:
            return response['history']
        elif 'candles' in response:
            return response['candles']
        elif 'trades' in response:
            return response['trades']
        else:
            return []

    except Exception as e:
        print(f"      Warning: Could not get history for {ticker}: {e}")
        return []


def detect_crossings(
    ticker: str,
    price_history: List[Dict],
    threshold: float = 0.90
) -> List[Dict]:
    """
    Detect every time price crossed above threshold

    Args:
        ticker: Market ticker
        price_history: List of price data points
        threshold: Price threshold (0.90 for 90¢)

    Returns:
        List of crossing events with:
        - cross_timestamp: When price crossed above threshold
        - cross_price: Price at crossing
        - dropped_back: Whether price later dropped below threshold
        - drop_timestamp: When it dropped back (if applicable)
        - held_minutes: How long it stayed above before dropping
    """
    if not price_history:
        return []

    crossings = []
    above_threshold = False
    current_crossing = None

    # Sort by timestamp
    sorted_history = sorted(
        price_history,
        key=lambda x: x.get('ts', x.get('timestamp', 0))
    )

    for point in sorted_history:
        # Get price - could be 'price', 'close', 'last_price', etc.
        price = None
        for field in ['price', 'close', 'last_price', 'yes_price']:
            if field in point:
                price = point[field]
                # Convert from cents to dollars if needed
                if isinstance(price, (int, float)) and price > 10:
                    price = price / 100.0
                break

        if price is None:
            continue

        timestamp = point.get('ts') or point.get('timestamp')
        if not timestamp:
            continue

        # Parse timestamp
        if isinstance(timestamp, str):
            ts = parse_datetime(timestamp)
        else:
            ts = datetime.fromtimestamp(timestamp)

        # Detect crossing above threshold
        if not above_threshold and price >= threshold:
            # Just crossed above!
            above_threshold = True
            current_crossing = {
                'cross_timestamp': ts,
                'cross_price': price,
                'dropped_back': False,
                'drop_timestamp': None,
                'held_minutes': None
            }

        # Detect drop back below threshold
        elif above_threshold and price < threshold:
            # Just dropped below!
            if current_crossing:
                current_crossing['dropped_back'] = True
                current_crossing['drop_timestamp'] = ts
                held_time = (ts - current_crossing['cross_timestamp']).total_seconds() / 60
                current_crossing['held_minutes'] = held_time
                crossings.append(current_crossing)

            above_threshold = False
            current_crossing = None

    # If still above threshold at end, record the crossing
    if above_threshold and current_crossing:
        crossings.append(current_crossing)

    return crossings


def analyze_market(
    client: KalshiClient,
    market: Dict,
    series_ticker: str
) -> List[Dict]:
    """
    Analyze a single market for 90¢ crossings

    Returns:
        List of crossing records (one per crossing)
    """
    ticker = market['ticker']

    # Get price history
    price_history = get_price_history(client, ticker)

    if not price_history:
        return []

    # Detect crossings
    crossings = detect_crossings(ticker, price_history, threshold=0.90)

    # Get market metadata
    close_time = parse_datetime(market.get('close_time'))
    result = market.get('result')  # 'yes' or 'no'

    # Enrich each crossing with market metadata
    records = []
    for crossing in crossings:
        record = {
            'series_ticker': series_ticker,
            'market_ticker': ticker,
            'market_title': market.get('title', ''),
            'cross_timestamp': crossing['cross_timestamp'].isoformat(),
            'cross_price': crossing['cross_price'],
            'dropped_back': crossing['dropped_back'],
            'drop_timestamp': crossing['drop_timestamp'].isoformat() if crossing['drop_timestamp'] else '',
            'held_minutes': crossing['held_minutes'] if crossing['held_minutes'] is not None else '',
            'close_time': close_time.isoformat(),
            'result': result,
            'would_have_won': (result == 'yes'),  # Assuming we bet YES when price >= 90¢
        }
        records.append(record)

    return records


def main():
    """Main execution"""

    print("=" * 80)
    print("COLLECTING 90¢ CROSSING DATA FROM KALSHI API")
    print("=" * 80)
    print()

    # Load config
    with open('/home/user/anthropic/kalshi-bot/config.yaml') as f:
        config = yaml.safe_load(f)

    # Initialize client
    client = KalshiClient(config)

    # Get top 5 series by volume
    top_series = get_top_volume_series(client, limit=5)
    print(f"Analyzing top {len(top_series)} series tickers:")
    for s in top_series:
        print(f"  - {s}")
    print()

    # Collect all crossing records
    all_records = []

    for series_ticker in top_series:
        print(f"\n{'=' * 80}")
        print(f"SERIES: {series_ticker}")
        print('=' * 80)

        # Get settled markets
        markets = get_settled_markets(client, series_ticker, days_back=30)

        if not markets:
            print(f"  No markets found")
            continue

        # Analyze each market
        print(f"  Analyzing {len(markets)} markets...")
        for i, market in enumerate(markets, 1):
            ticker = market['ticker']

            if i % 10 == 0:
                print(f"    Progress: {i}/{len(markets)} markets...")

            records = analyze_market(client, market, series_ticker)
            all_records.extend(records)

            # Rate limiting - 2 requests per second
            time.sleep(0.5)

        print(f"  ✅ Found {len([r for r in all_records if r['series_ticker'] == series_ticker])} crossings")

    # Save to CSV
    print(f"\n{'=' * 80}")
    print("SAVING RESULTS")
    print('=' * 80)

    output_file = 'crossing_data_top5.csv'

    if all_records:
        with open(output_file, 'w', newline='') as f:
            fieldnames = [
                'series_ticker',
                'market_ticker',
                'market_title',
                'cross_timestamp',
                'cross_price',
                'dropped_back',
                'drop_timestamp',
                'held_minutes',
                'close_time',
                'result',
                'would_have_won'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"\n✅ Saved {len(all_records)} crossing records to {output_file}")
        print()
        print("Summary by series:")

        series_summary = {}
        for record in all_records:
            series = record['series_ticker']
            if series not in series_summary:
                series_summary[series] = {
                    'total_crossings': 0,
                    'dropped_back': 0,
                    'wins': 0
                }
            series_summary[series]['total_crossings'] += 1
            if record['dropped_back']:
                series_summary[series]['dropped_back'] += 1
            if record['would_have_won']:
                series_summary[series]['wins'] += 1

        for series, stats in series_summary.items():
            total = stats['total_crossings']
            dropped = stats['dropped_back']
            wins = stats['wins']
            drop_rate = (dropped / total * 100) if total > 0 else 0
            win_rate = (wins / total * 100) if total > 0 else 0

            print(f"  {series}:")
            print(f"    Total crossings: {total}")
            print(f"    Dropped back: {dropped} ({drop_rate:.1f}%)")
            print(f"    Would have won: {wins} ({win_rate:.1f}%)")
    else:
        print("\n⚠️  No crossing data found")

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == '__main__':
    main()
