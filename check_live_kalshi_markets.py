"""
Fetch active markets from Kalshi and cross-reference with backtest accuracy.

Shows:
1. All active series on Kalshi right now (extracted from event_ticker)
2. Which ones have games happening TODAY (truly live)
3. Their accuracy from our backtest (90-92¢ range)
4. Whether profitable at 91¢ entry

Fetches markets per known backtest series, uses expected_expiration_time
to determine which games are happening today vs. future.
"""

import os
import sys
import re
import pandas as pd
from datetime import datetime, timezone, timedelta

# Add kalshi-bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kalshi-bot'))

from kalshi_client import KalshiClient


def extract_series_from_event(event_ticker):
    """Extract series ticker from event_ticker (e.g. KXNBAGAME-26FEB25BOSDEN -> KXNBAGAME)"""
    if not event_ticker:
        return None
    parts = event_ticker.split('-')
    return parts[0] if parts else None


def main():
    print("=" * 100)
    print("KALSHI LIVE MARKETS - CROSS-REFERENCED WITH BACKTEST ACCURACY")
    print("=" * 100)
    print()

    now = datetime.now(timezone.utc)
    print(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
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
        print("Connected to Kalshi API")
        print()
    except Exception as e:
        print(f"Error connecting to Kalshi: {e}")
        print()
        print("Make sure you have:")
        print("  - KALSHI_API_KEY_ID environment variable set")
        print("  - KALSHI_PRIVATE_KEY_PATH environment variable set")
        return

    # Load backtest accuracy data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Filter to 90-92¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Loaded backtest data: {len(price_df):,} markets in 90-92¢ range")

    # Calculate accuracy for each series ticker from backtest
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

    backtest_series = list(df['Series Ticker'].unique())
    print(f"Backtest covers {len(backtest_series)} unique series tickers")
    print()

    # Fetch markets for each backtest series using the category filter
    print(f"Fetching active markets for each backtest series...")
    print(f"(Querying {len(backtest_series)} series - this may take a minute)")
    print()

    all_markets = []
    series_with_markets = 0

    for i, series in enumerate(backtest_series):
        try:
            markets = client.get_markets(category=series, limit=1000, max_total=1000)
            if markets:
                for m in markets:
                    m['_series'] = series  # tag with series
                all_markets.extend(markets)
                series_with_markets += 1
        except Exception as e:
            pass  # Series might not exist on current API

        if (i + 1) % 50 == 0:
            print(f"  Queried {i+1}/{len(backtest_series)} series... ({len(all_markets)} markets so far)")

    print(f"\nTotal active markets found: {len(all_markets)} across {series_with_markets} series")
    print()

    # Classify markets by timing
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    tomorrow_end = today_start + timedelta(days=2)

    # Show sample timestamps
    print("=" * 100)
    print("SAMPLE MARKET TIMESTAMPS (verifying live status)")
    print("=" * 100)
    print()

    samples_shown = 0
    for m in all_markets:
        if samples_shown >= 10:
            break
        exp = m.get('expected_expiration_time', '')
        close = m.get('close_time', '')
        title = m.get('title', 'N/A')[:70]
        series = m.get('_series', 'N/A')

        if exp:
            try:
                exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                hours_until = (exp_dt - now).total_seconds() / 3600

                if -6 < hours_until < 24:  # Recently expired or expiring today
                    label = "LIVE NOW" if hours_until < 6 else "TODAY"
                    if hours_until < 0:
                        label = "JUST ENDED"
                    print(f"  [{label}] {title}")
                    print(f"    Series: {series}")
                    print(f"    Expected expiration: {exp}")
                    print(f"    Close time: {close}")
                    print(f"    Hours until expiration: {hours_until:.1f}")
                    print()
                    samples_shown += 1
            except:
                pass

    if samples_shown == 0:
        # Show some samples anyway
        for m in all_markets[:5]:
            exp = m.get('expected_expiration_time', '')
            close = m.get('close_time', '')
            title = m.get('title', 'N/A')[:70]
            series = m.get('_series', 'N/A')
            if exp:
                exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                hours_until = (exp_dt - now).total_seconds() / 3600
                print(f"  {title}")
                print(f"    Series: {series}")
                print(f"    Expected expiration: {exp}")
                print(f"    Close time: {close}")
                print(f"    Hours until expiration: {hours_until:.1f}")
                print()

    # Group by series and classify timing
    series_data = {}
    for m in all_markets:
        series = m.get('_series', 'UNKNOWN')
        if series not in series_data:
            series_data[series] = {
                'total': 0,
                'live_now': 0,        # expiring within 6 hours
                'today': 0,           # expiring within 24 hours
                'upcoming': 0,        # expiring later
                'example_title': m.get('title', ''),
                'example_exp': m.get('expected_expiration_time', ''),
            }

        series_data[series]['total'] += 1
        exp = m.get('expected_expiration_time', '')
        if exp:
            try:
                exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                hours_until = (exp_dt - now).total_seconds() / 3600
                if 0 <= hours_until < 6:
                    series_data[series]['live_now'] += 1
                elif 0 <= hours_until < 24:
                    series_data[series]['today'] += 1
                else:
                    series_data[series]['upcoming'] += 1
            except:
                series_data[series]['upcoming'] += 1

    # Build results
    results = []
    for series, info in series_data.items():
        acc_data = ticker_accuracy.get(series)
        if acc_data:
            accuracy = acc_data['accuracy']
            backtest_n = acc_data['total_markets']
            wins = acc_data['wins']
            win_prob = accuracy / 100
            fee = 0.01
            total_cost = 0.91 + fee
            profit_if_win = 1.00 - total_cost
            loss_if_lose = -total_cost
            expected_profit = (win_prob * profit_if_win) + ((1 - win_prob) * loss_if_lose)
            has_backtest = True
            profitable = expected_profit > 0
        else:
            accuracy = 0
            backtest_n = 0
            wins = 0
            expected_profit = 0
            has_backtest = True  # All queried series should have backtest
            profitable = False

        results.append({
            'series': series,
            'total_markets': info['total'],
            'live_now': info['live_now'],
            'today': info['today'],
            'upcoming': info['upcoming'],
            'backtest_n': backtest_n,
            'wins': wins,
            'accuracy': accuracy,
            'expected_profit': expected_profit,
            'profitable': profitable,
            'example_title': info['example_title'][:60],
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(['live_now', 'today', 'accuracy'], ascending=[False, False, False])

    # Save
    results_df.to_csv('truly_live_kalshi_markets_with_accuracy.csv', index=False)

    # Count truly live
    total_live_now = results_df['live_now'].sum()
    total_today = results_df['today'].sum()
    total_upcoming = results_df['upcoming'].sum()
    total_all = results_df['total_markets'].sum()

    print("=" * 100)
    print("HOW MANY MARKETS ARE TRULY LIVE?")
    print("=" * 100)
    print()
    print(f"  LIVE NOW (expiring within 6 hrs):   {total_live_now:>6} markets")
    print(f"  TODAY (expiring within 24 hrs):      {total_today:>6} markets")
    print(f"  UPCOMING (expiring later):           {total_upcoming:>6} markets")
    print(f"  TOTAL active markets:                {total_all:>6} markets")
    print(f"  Across {len(results_df)} series with active markets")
    print()

    # Series with live-now games
    live_series = results_df[results_df['live_now'] > 0]
    if len(live_series) > 0:
        print("=" * 140)
        print("SERIES WITH GAMES HAPPENING RIGHT NOW (expiring within 6 hours)")
        print("=" * 140)
        print()
        print(f"{'Series':<30} {'Live Now':>10} {'Today':>8} {'Total':>8} {'Backtest':>10} {'Accuracy':>10} {'Profit/Bet':>12} {'Status':>15}")
        print("-" * 140)

        for _, row in live_series.iterrows():
            status = "PROFITABLE" if row['profitable'] else "LOSING"
            print(f"{row['series']:<30} {row['live_now']:>10} {row['today']:>8} {row['total_markets']:>8} "
                  f"{row['backtest_n']:>10} {row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f} {status:>15}")
        print()
    else:
        print("No games are happening RIGHT NOW (no markets expiring within 6 hours)")
        print("(This is normal during off-hours - most US sports play in the evening)")
        print()

    # Series with games today
    today_series = results_df[results_df['today'] > 0]
    if len(today_series) > 0:
        print("=" * 140)
        print("SERIES WITH GAMES TODAY (expiring within 24 hours)")
        print("=" * 140)
        print()
        print(f"{'Series':<30} {'Today':>8} {'Total':>8} {'Backtest':>10} {'Accuracy':>10} {'Profit/Bet':>12} {'Status':>15}")
        print("-" * 140)

        for _, row in today_series.iterrows():
            status = "PROFITABLE" if row['profitable'] else "LOSING"
            print(f"{row['series']:<30} {row['today']:>8} {row['total_markets']:>8} "
                  f"{row['backtest_n']:>10} {row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f} {status:>15}")
        print()

    # ALL series with active markets
    print("=" * 140)
    print(f"ALL {len(results_df)} SERIES WITH ACTIVE MARKETS - SORTED BY ACCURACY")
    print("=" * 140)
    print()

    by_accuracy = results_df.sort_values('accuracy', ascending=False)
    print(f"{'Series':<30} {'Acc%':>8} {'Profit/Bet':>12} {'Live':>6} {'Today':>7} {'Total':>7} {'Backtest':>10} {'Example':<40}")
    print("-" * 140)

    for _, row in by_accuracy.iterrows():
        live_marker = " *" if row['live_now'] > 0 else ""
        print(f"{row['series']:<30} {row['accuracy']:>7.1f}% ${row['expected_profit']:>10.4f} "
              f"{row['live_now']:>6} {row['today']:>7} {row['total_markets']:>7} "
              f"{row['backtest_n']:>10} {row['example_title']:<40}{live_marker}")

    print()

    # Summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()

    profitable_series = results_df[results_df['profitable']]
    losing_series = results_df[~results_df['profitable']]

    print(f"Total series with active markets: {len(results_df)}")
    print(f"  Profitable at 91¢ entry: {len(profitable_series)} ({len(profitable_series)/len(results_df)*100:.0f}%)")
    print(f"  Losing at 91¢ entry: {len(losing_series)} ({len(losing_series)/len(results_df)*100:.0f}%)")
    print()

    if len(profitable_series) > 0:
        print(f"Top 10 most profitable series:")
        top = profitable_series.sort_values('expected_profit', ascending=False).head(10)
        for _, row in top.iterrows():
            print(f"  {row['series']:<30} {row['accuracy']:.1f}% acc, ${row['expected_profit']:.4f}/bet, {row['total_markets']} active markets")
    print()

    print(f"Saved to: truly_live_kalshi_markets_with_accuracy.csv")
    print()


if __name__ == "__main__":
    main()
