"""
Fetch LIVE markets from Kalshi (games happening RIGHT NOW) and cross-reference with backtest accuracy.

Shows:
1. All LIVE series tickers on Kalshi right now (events currently in progress)
2. Their accuracy from our backtest (90-92¢ range)
3. Number of live markets per ticker
4. Whether profitable at 91¢ entry

Uses is_live='true' API filter to get only markets where the event has already started
and is still ongoing (not future games, not completed games).
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add kalshi-bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kalshi-bot'))

from kalshi_client import KalshiClient

def main():
    print("=" * 100)
    print("FETCHING LIVE KALSHI MARKETS")
    print("=" * 100)
    print()

    # Initialize Kalshi client
    try:
        config = {
            'kalshi_api_base': "https://api.elections.kalshi.com/trade-api/v2",
            'api_requests_per_second': 2,
            'retry_max_attempts': 3,
            'retry_backoff_seconds': 2
        }
        client = KalshiClient(config)
        print("✅ Connected to Kalshi API")
        print()
    except Exception as e:
        print(f"❌ Error connecting to Kalshi: {e}")
        print()
        print("Make sure you have:")
        print("  - KALSHI_API_KEY_ID environment variable set")
        print("  - KALSHI_PRIVATE_KEY_PATH environment variable set")
        return

    # Fetch LIVE markets (games happening RIGHT NOW)
    print("Fetching LIVE markets (games currently in progress)...")
    try:
        markets = client.get_markets(is_live='true', limit=5000)
        print(f"✅ Found {len(markets)} LIVE markets (games happening RIGHT NOW)")
        print()
    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        return

    # Also show sample timestamps to verify
    if len(markets) > 0:
        print("Sample market timestamps (verifying live status):")
        for market in markets[:3]:
            print(f"  Market: {market.get('title', 'N/A')[:60]}")
            print(f"    close_time: {market.get('close_time', 'N/A')}")
            if 'event' in market:
                event = market['event']
                for key in event.keys():
                    if 'time' in key.lower() or 'date' in key.lower():
                        print(f"    event.{key}: {event[key]}")
            print()
        print()

    # Extract series tickers
    series_tickers = {}
    for market in markets:
        series_ticker = market.get('series_ticker', 'UNKNOWN')
        ticker = market.get('ticker', '')
        title = market.get('title', '')
        category = market.get('category', '')

        if series_ticker not in series_tickers:
            series_tickers[series_ticker] = {
                'count': 0,
                'category': category,
                'example_title': title,
                'example_ticker': ticker
            }

        series_tickers[series_ticker]['count'] += 1

    print(f"Found {len(series_tickers)} unique series tickers")
    print()

    # Load backtest accuracy data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Filter to 90-92¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Loaded backtest data: {len(price_df):,} markets in 90-92¢ range")
    print()

    # Calculate accuracy for each series ticker
    ticker_accuracy = {}
    for ticker in df['Series Ticker'].unique():
        ticker_markets = price_df[price_df['Series Ticker'] == ticker]

        if len(ticker_markets) > 0:
            total = len(ticker_markets)
            wins = (ticker_markets['Prediction Correct'] == 'CORRECT').sum()
            accuracy = (wins / total) * 100 if total > 0 else 0

            ticker_accuracy[ticker] = {
                'total_markets': total,
                'wins': wins,
                'accuracy': accuracy
            }

    # Cross-reference live markets with backtest data
    results = []

    for series_ticker, info in series_tickers.items():
        category = info['category']
        live_count = info['count']
        example_title = info['example_title']

        if series_ticker in ticker_accuracy:
            acc_data = ticker_accuracy[series_ticker]
            backtest_markets = acc_data['total_markets']
            wins = acc_data['wins']
            accuracy = acc_data['accuracy']

            # Calculate expected profit at 91¢ entry
            if accuracy > 0:
                win_prob = accuracy / 100
                fee = 0.01  # 7% fee at 91¢
                total_cost = 0.91 + fee
                profit_if_win = 1.00 - total_cost
                loss_if_lose = -total_cost
                expected_profit = (win_prob * profit_if_win) + ((1 - win_prob) * loss_if_lose)
            else:
                expected_profit = 0

            has_backtest = True
            profitable = expected_profit > 0
        else:
            backtest_markets = 0
            wins = 0
            accuracy = 0
            expected_profit = 0
            has_backtest = False
            profitable = False

        results.append({
            'series_ticker': series_ticker,
            'category': category,
            'live_markets': live_count,
            'has_backtest': has_backtest,
            'backtest_markets': backtest_markets,
            'wins': wins,
            'accuracy': accuracy,
            'expected_profit': expected_profit,
            'profitable': profitable,
            'example_title': example_title
        })

    # Convert to DataFrame and sort
    results_df = pd.DataFrame(results)

    # Sort by: has_backtest (yes first), then by accuracy (desc), then by live_markets (desc)
    results_df = results_df.sort_values(
        ['has_backtest', 'accuracy', 'live_markets'],
        ascending=[False, False, False]
    )

    # Save full results
    results_df.to_csv('truly_live_kalshi_markets_with_accuracy.csv', index=False)

    print("=" * 140)
    print("TRULY LIVE KALSHI MARKETS (Games Happening RIGHT NOW) - CROSS-REFERENCED WITH BACKTEST ACCURACY")
    print("=" * 140)
    print()

    print(f"{'Series Ticker':<30} {'Category':<20} {'Live':>6} {'Backtest':>10} {'Accuracy':>10} {'Profit/Bet':>12} {'Status':>15}")
    print("-" * 140)

    for idx, row in results_df.iterrows():
        if row['has_backtest']:
            status = "✅ Profitable" if row['profitable'] else "❌ Losing"
            print(f"{row['series_ticker']:<30} {row['category']:<20} {row['live_markets']:>6} "
                  f"{row['backtest_markets']:>10} {row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f} {status:>15}")
        else:
            print(f"{row['series_ticker']:<30} {row['category']:<20} {row['live_markets']:>6} "
                  f"{'NO DATA':>10} {'N/A':>10} {'N/A':>12} {'⚠️  Unknown':>15}")

    print()

    # Summary statistics
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()

    total_live = len(results_df)
    with_backtest = results_df['has_backtest'].sum()
    without_backtest = total_live - with_backtest
    profitable_count = results_df['profitable'].sum()
    losing_count = with_backtest - profitable_count

    print(f"Total live series tickers: {total_live}")
    print(f"  With backtest data: {with_backtest} ({with_backtest/total_live*100:.1f}%)")
    print(f"  Without backtest data: {without_backtest} ({without_backtest/total_live*100:.1f}%)")
    print()

    if with_backtest > 0:
        print(f"Of those with backtest data:")
        print(f"  Profitable (>0 profit/bet): {profitable_count} ({profitable_count/with_backtest*100:.1f}%)")
        print(f"  Losing (≤0 profit/bet): {losing_count} ({losing_count/with_backtest*100:.1f}%)")
    print()

    # Breakdown by category
    print("=" * 100)
    print("BREAKDOWN BY CATEGORY")
    print("=" * 100)
    print()

    category_breakdown = results_df.groupby('category').agg({
        'live_markets': 'sum',
        'has_backtest': 'sum',
        'profitable': 'sum'
    }).sort_values('live_markets', ascending=False)

    print(f"{'Category':<30} {'Live Markets':>15} {'With Backtest':>15} {'Profitable':>15}")
    print("-" * 100)

    for category, row in category_breakdown.iterrows():
        print(f"{category:<30} {int(row['live_markets']):>15} {int(row['has_backtest']):>15} {int(row['profitable']):>15}")

    print()

    # Check for Olympics
    print("=" * 100)
    print("WINTER OLYMPICS CHECK")
    print("=" * 100)
    print()

    olympics_tickers = results_df[
        results_df['series_ticker'].str.contains('OLYMPIC|OLYM|WINTER', case=False, na=False)
    ]

    if len(olympics_tickers) > 0:
        print(f"Found {len(olympics_tickers)} Olympics-related tickers:")
        print()

        for idx, row in olympics_tickers.iterrows():
            print(f"  {row['series_ticker']}: {row['live_markets']} markets")
            print(f"    Category: {row['category']}")
            print(f"    Example: {row['example_title']}")
            if row['has_backtest']:
                print(f"    Backtest: {row['backtest_markets']} markets, {row['accuracy']:.1f}% accurate")
            else:
                print(f"    Backtest: NO DATA")
            print()
    else:
        print("No Olympics-related tickers found")
        print()

        # Check for winter sports
        winter_sports = results_df[
            results_df['category'].str.contains('Winter|Skiing|Snowboard|Ice|Hockey', case=False, na=False) |
            results_df['series_ticker'].str.contains('SKI|SNOW|ICE', case=False, na=False)
        ]

        if len(winter_sports) > 0:
            print(f"Found {len(winter_sports)} winter sports tickers:")
            print()

            for idx, row in winter_sports.iterrows():
                print(f"  {row['series_ticker']}: {row['live_markets']} markets ({row['category']})")
                if row['has_backtest']:
                    print(f"    Backtest: {row['accuracy']:.1f}% accurate (n={row['backtest_markets']})")
                print()

    # Top profitable tickers currently live
    print("=" * 100)
    print("TOP 20 MOST PROFITABLE TICKERS (currently live)")
    print("=" * 100)
    print()

    profitable_live = results_df[results_df['profitable']].head(20)

    print(f"{'Rank':<6} {'Ticker':<30} {'Category':<20} {'Accuracy':>10} {'Profit/Bet':>12} {'Live':>8}")
    print("-" * 120)

    for rank, (idx, row) in enumerate(profitable_live.iterrows(), 1):
        print(f"{rank:<6} {row['series_ticker']:<30} {row['category']:<20} {row['accuracy']:>9.1f}% "
              f"${row['expected_profit']:>10.4f} {row['live_markets']:>8}")

    print()

    # Untested but live tickers
    print("=" * 100)
    print("UNTESTED TICKERS (no backtest data, might be new)")
    print("=" * 100)
    print()

    untested = results_df[~results_df['has_backtest']].head(20)

    if len(untested) > 0:
        print(f"{'Series Ticker':<30} {'Category':<30} {'Live Markets':>15}")
        print("-" * 100)

        for idx, row in untested.iterrows():
            print(f"{row['series_ticker']:<30} {row['category']:<30} {row['live_markets']:>15}")
    else:
        print("All live tickers have backtest data!")

    print()

    print("✅ Saved to: truly_live_kalshi_markets_with_accuracy.csv")
    print()

if __name__ == "__main__":
    main()
