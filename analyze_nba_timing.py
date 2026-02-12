"""
Analyze profitability of NBA markets by game timing.
Calculate time_elapsed_pct = (first_touch_time - open_time) / (close_time - open_time)
Bucket by: 0-25%, 25-50%, 50-75%, 75-100%
"""

import pandas as pd
import requests
from datetime import datetime
import time
from collections import defaultdict

# Profitable NBA series tickers
PROFITABLE_SERIES = ['KXNBAGAME', 'KXNBASPREAD', 'KXNBAREB', 'KXNBATOTAL']

def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime."""
    if pd.isna(ts_str):
        return None
    try:
        return pd.to_datetime(ts_str, format='ISO8601')
    except:
        return None

def get_market_details(ticker, max_retries=3):
    """Fetch market details from Kalshi API to get open_time."""
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'market' in data:
                    return data['market']
            elif response.status_code == 429:
                # Rate limited, wait and retry
                wait_time = 2 ** attempt
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return None
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)

    return None

def calculate_time_elapsed_pct(first_touch, open_time, close_time):
    """Calculate what % through the event lifetime we are at first touch."""
    if not all([first_touch, open_time, close_time]):
        return None

    try:
        first_touch_dt = parse_timestamp(first_touch)
        open_time_dt = parse_timestamp(open_time)
        close_time_dt = parse_timestamp(close_time)

        if not all([first_touch_dt, open_time_dt, close_time_dt]):
            return None

        total_duration = (close_time_dt - open_time_dt).total_seconds()
        elapsed = (first_touch_dt - open_time_dt).total_seconds()

        if total_duration <= 0:
            return None

        return (elapsed / total_duration) * 100
    except:
        return None

def get_time_bucket(pct):
    """Bucket time_elapsed_pct into 4 quartiles."""
    if pct is None or pct < 0 or pct > 100:
        return 'Unknown'
    elif pct <= 25:
        return '0-25%'
    elif pct <= 50:
        return '25-50%'
    elif pct <= 75:
        return '50-75%'
    else:
        return '75-100%'

def analyze_nba_timing():
    """Main analysis function."""

    print("=" * 100)
    print("NBA TIMING ANALYSIS: Profitability by Game Phase")
    print("=" * 100)
    print()

    # Load data
    print("Loading backtest data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Filter for profitable NBA series
    nba_df = df[df['Series Ticker'].isin(PROFITABLE_SERIES)].copy()

    print(f"Found {len(nba_df):,} markets from profitable NBA series:")
    for series in PROFITABLE_SERIES:
        count = len(nba_df[nba_df['Series Ticker'] == series])
        print(f"  {series}: {count:,} markets")
    print()

    # Enrich with market open_time
    print("Fetching market open times from Kalshi API...")
    print("(This may take a few minutes due to rate limiting)")
    print()

    open_times = {}
    failed = []

    for idx, row in nba_df.iterrows():
        ticker = row['Ticker']

        if idx % 50 == 0:
            print(f"  Progress: {idx}/{len(nba_df)} ({idx/len(nba_df)*100:.1f}%)")

        # Check if we already have it
        if ticker in open_times:
            continue

        # Fetch from API
        market_data = get_market_details(ticker)

        if market_data and 'open_time' in market_data:
            open_times[ticker] = market_data['open_time']
        else:
            failed.append(ticker)

        # Rate limit: 2 requests per second
        time.sleep(0.5)

    print(f"\nSuccessfully fetched {len(open_times):,} open times")
    print(f"Failed to fetch {len(failed):,} markets")
    print()

    # Add open_time to dataframe
    nba_df['Market Open Time'] = nba_df['Ticker'].map(open_times)

    # Calculate time_elapsed_pct
    nba_df['Time_Elapsed_Pct'] = nba_df.apply(
        lambda row: calculate_time_elapsed_pct(
            row['First Touch Time'],
            row['Market Open Time'],
            row['Market Close Time']
        ),
        axis=1
    )

    # Add time bucket
    nba_df['Time_Bucket'] = nba_df['Time_Elapsed_Pct'].apply(get_time_bucket)

    # Filter out rows without timing data
    valid_df = nba_df[nba_df['Time_Bucket'] != 'Unknown'].copy()

    print(f"Markets with valid timing data: {len(valid_df):,} / {len(nba_df):,}")
    print()

    # Calculate profitability metrics by bucket
    print("=" * 100)
    print("RESULTS BY GAME PHASE")
    print("=" * 100)
    print()

    buckets = ['0-25%', '25-50%', '50-75%', '75-100%']

    for bucket in buckets:
        bucket_df = valid_df[valid_df['Time_Bucket'] == bucket]

        if len(bucket_df) == 0:
            print(f"{bucket}: No data")
            print()
            continue

        # Calculate metrics
        total = len(bucket_df)
        correct = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
        wrong = (bucket_df['Prediction Correct'] == 'WRONG').sum()
        accuracy = (correct / total) * 100

        # Calculate profitability (assuming 1¢ bet on each market)
        avg_price = bucket_df['First Touch Price (¢)'].mean()

        # Profit per trade = (100¢ - entry_price) if win, -entry_price if loss
        bucket_df['Profit'] = bucket_df.apply(
            lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
                       else -row['First Touch Price (¢)'],
            axis=1
        )

        total_profit = bucket_df['Profit'].sum()
        avg_profit_per_trade = bucket_df['Profit'].mean()
        roi = (total_profit / (bucket_df['First Touch Price (¢)'].sum())) * 100

        print(f"📊 {bucket} (First {bucket.split('-')[0]} of game time)")
        print(f"   Markets: {total:,}")
        print(f"   Correct: {correct:,} ({accuracy:.1f}%)")
        print(f"   Wrong: {wrong:,} ({100-accuracy:.1f}%)")
        print(f"   Avg entry price: {avg_price:.1f}¢")
        print(f"   Avg profit per trade: {avg_profit_per_trade:.2f}¢")
        print(f"   Total profit: {total_profit:.2f}¢")
        print(f"   ROI: {roi:.2f}%")
        print()

    # Save enriched data
    output_file = 'nba_timing_analysis.csv'
    valid_df.to_csv(output_file, index=False)
    print(f"Saved detailed data to {output_file}")
    print()

    # Per-series breakdown
    print("=" * 100)
    print("BREAKDOWN BY SERIES AND TIME BUCKET")
    print("=" * 100)
    print()

    for series in PROFITABLE_SERIES:
        series_df = valid_df[valid_df['Series Ticker'] == series]

        if len(series_df) == 0:
            continue

        print(f"\n{series} ({len(series_df):,} markets)")
        print("-" * 80)

        for bucket in buckets:
            bucket_df = series_df[series_df['Time_Bucket'] == bucket]

            if len(bucket_df) == 0:
                continue

            correct = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
            total = len(bucket_df)
            accuracy = (correct / total) * 100

            bucket_df['Profit'] = bucket_df.apply(
                lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
                           else -row['First Touch Price (¢)'],
                axis=1
            )

            avg_profit = bucket_df['Profit'].mean()

            print(f"  {bucket}: {total:,} markets | {accuracy:.1f}% accuracy | {avg_profit:+.2f}¢ avg profit")

if __name__ == "__main__":
    analyze_nba_timing()
