"""
Timing + Price analysis with recency dimension.

Splits data into:
- "old": before Jan 2025
- "recent": Jan 2025 onwards

For each sub-category with 50+ markets AND 80%+ accuracy, analyze by:
- Period: old vs recent
- Time bucket: 0-25%, 25-50%, 50-75%, 75-100%
- Price bucket: 90-92¢, 93-95¢, 96-98¢
"""

import pandas as pd
import requests
from datetime import datetime
import time
from map_kalshi_subcategories import map_to_subcategory

RECENCY_CUTOFF = datetime(2025, 1, 1, tzinfo=None)

def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime."""
    if pd.isna(ts_str):
        return None
    try:
        dt = pd.to_datetime(ts_str, format='ISO8601')
        # Remove timezone for comparison
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except:
        return None

def get_period(settlement_date):
    """Determine if market is 'old' or 'recent'."""
    if pd.isna(settlement_date):
        return 'Unknown'

    try:
        dt = parse_timestamp(settlement_date)
        if dt is None:
            return 'Unknown'

        if dt < RECENCY_CUTOFF:
            return 'old'
        else:
            return 'recent'
    except:
        return 'Unknown'

def get_market_open_time(ticker, cache, max_retries=3):
    """Fetch market open_time from Kalshi API with caching."""
    if ticker in cache:
        return cache[ticker]

    url = f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'market' in data and 'open_time' in data['market']:
                    open_time = data['market']['open_time']
                    cache[ticker] = open_time
                    return open_time
            elif response.status_code == 429:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            else:
                cache[ticker] = None
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)

    cache[ticker] = None
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
    """Bucket time_elapsed_pct into quartiles."""
    if pct is None or pct < 0:
        return 'Unknown'
    elif pct <= 25:
        return '0-25%'
    elif pct <= 50:
        return '25-50%'
    elif pct <= 75:
        return '50-75%'
    elif pct <= 100:
        return '75-100%'
    else:
        return '>100%'

def get_price_bucket(price):
    """Bucket price into ranges."""
    if pd.isna(price):
        return 'Unknown'
    elif 90 <= price < 93:
        return '90-92¢'
    elif 93 <= price < 96:
        return '93-95¢'
    elif 96 <= price <= 98:
        return '96-98¢'
    else:
        return 'Other'

def analyze_with_recency():
    """Main analysis function."""

    print("=" * 100)
    print("TIMING + PRICE ANALYSIS WITH RECENCY DIMENSION")
    print(f"Splitting: 'old' (before Jan 2025) vs 'recent' (Jan 2025+)")
    print("=" * 100)
    print()

    # Load data
    print("Loading backtest data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Map to sub-categories
    print("Mapping to hierarchical sub-categories...")
    df['Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[0],
        axis=1
    )
    df['Sub_Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[1],
        axis=1
    )

    df['Hierarchical_Path'] = df.apply(
        lambda row: f"{row['Category']} > {row['Sub_Category']}" if pd.isna(row['Sub_Sub_Category'])
                    else f"{row['Category']} > {row['Sub_Category']} > {row['Sub_Sub_Category']}",
        axis=1
    )

    # Add period column
    print("Determining recency periods...")
    df['Period'] = df['Market Close Time'].apply(get_period)

    # Calculate accuracy and count per sub-category (overall)
    print("Calculating sub-category metrics...")
    subcategory_stats = df.groupby('Hierarchical_Path').agg({
        'Prediction Correct': [
            ('total', 'count'),
            ('correct', lambda x: (x == 'CORRECT').sum())
        ]
    }).reset_index()

    subcategory_stats.columns = ['Hierarchical_Path', 'total', 'correct']
    subcategory_stats['accuracy'] = (subcategory_stats['correct'] / subcategory_stats['total']) * 100

    # Filter: 50+ markets AND 80%+ accuracy
    eligible = subcategory_stats[
        (subcategory_stats['total'] >= 50) &
        (subcategory_stats['accuracy'] >= 80.0)
    ].copy()

    eligible = eligible.sort_values('total', ascending=False)

    print(f"\nFound {len(eligible)} eligible sub-categories")
    print()

    # Show recency breakdown
    eligible_paths = set(eligible['Hierarchical_Path'].values)
    analysis_df = df[df['Hierarchical_Path'].isin(eligible_paths)].copy()

    old_count = (analysis_df['Period'] == 'old').sum()
    recent_count = (analysis_df['Period'] == 'recent').sum()
    unknown_count = (analysis_df['Period'] == 'Unknown').sum()

    print(f"Total markets to analyze: {len(analysis_df):,}")
    print(f"  Old (before Jan 2025): {old_count:,}")
    print(f"  Recent (Jan 2025+): {recent_count:,}")
    print(f"  Unknown period: {unknown_count:,}")
    print()

    # Fetch open times
    print("Fetching market open times from Kalshi API...")
    print("(This will take several minutes due to rate limiting)")
    print()

    open_time_cache = {}
    failed_count = 0

    for idx, row in analysis_df.iterrows():
        ticker = row['Ticker']

        if idx % 100 == 0:
            pct = (idx / len(analysis_df)) * 100
            cached_count = len([v for v in open_time_cache.values() if v is not None])
            print(f"  Progress: {len(open_time_cache)}/{len(analysis_df)} ({pct:.1f}%) | "
                  f"Successful: {cached_count} | Failed: {failed_count}")

        if ticker not in open_time_cache:
            open_time = get_market_open_time(ticker, open_time_cache)
            if open_time is None:
                failed_count += 1

            # Rate limit: 2 requests per second
            time.sleep(0.5)

    successful_count = len([v for v in open_time_cache.values() if v is not None])
    print(f"\n✅ Fetching complete")
    print(f"   Successfully fetched: {successful_count:,}")
    print(f"   Failed: {failed_count:,}")
    print()

    # Add timing data
    analysis_df['Market Open Time'] = analysis_df['Ticker'].map(open_time_cache)

    print("Calculating timing metrics...")
    analysis_df['Time_Elapsed_Pct'] = analysis_df.apply(
        lambda row: calculate_time_elapsed_pct(
            row['First Touch Time'],
            row['Market Open Time'],
            row['Market Close Time']
        ),
        axis=1
    )

    analysis_df['Time_Bucket'] = analysis_df['Time_Elapsed_Pct'].apply(get_time_bucket)
    analysis_df['Price_Bucket'] = analysis_df['First Touch Price (¢)'].apply(get_price_bucket)

    # Filter valid data
    valid_df = analysis_df[
        (analysis_df['Period'] != 'Unknown') &
        (analysis_df['Time_Bucket'] != 'Unknown') &
        (analysis_df['Price_Bucket'] != 'Unknown') &
        (analysis_df['Price_Bucket'] != 'Other')
    ].copy()

    print(f"Markets with valid timing + price + period data: {len(valid_df):,} / {len(analysis_df):,}")
    print()

    # Calculate profit
    valid_df['Profit'] = valid_df.apply(
        lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
                   else -row['First Touch Price (¢)'],
        axis=1
    )

    # Aggregate by period, sub-category, series ticker, time bucket, and price bucket
    print("Aggregating results...")

    results = []

    for period in ['old', 'recent']:
        period_df = valid_df[valid_df['Period'] == period]

        for path in sorted(eligible_paths):
            path_df = period_df[period_df['Hierarchical_Path'] == path]

            if len(path_df) == 0:
                continue

            series_tickers = path_df['Series Ticker'].unique()

            for series_ticker in series_tickers:
                series_df = path_df[path_df['Series Ticker'] == series_ticker]

                for time_bucket in ['0-25%', '25-50%', '50-75%', '75-100%', '>100%']:
                    time_df = series_df[series_df['Time_Bucket'] == time_bucket]

                    if len(time_df) == 0:
                        continue

                    for price_bucket in ['90-92¢', '93-95¢', '96-98¢']:
                        bucket_df = time_df[time_df['Price_Bucket'] == price_bucket]

                        if len(bucket_df) == 0:
                            continue

                        total = len(bucket_df)
                        wins = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
                        losses = total - wins
                        accuracy = (wins / total) * 100
                        avg_profit = bucket_df['Profit'].mean()
                        profitable = 'yes' if avg_profit > 0 else 'no'

                        results.append({
                            'period': period,
                            'sub_category': path,
                            'series_ticker': series_ticker,
                            'time_bucket': time_bucket,
                            'price_bucket': price_bucket,
                            'total_markets': total,
                            'wins': wins,
                            'losses': losses,
                            'accuracy': round(accuracy, 1),
                            'avg_profit': round(avg_profit, 2),
                            'profitable_yes_no': profitable
                        })

    # Create output dataframe
    results_df = pd.DataFrame(results)

    # Sort
    results_df = results_df.sort_values(
        ['period', 'profitable_yes_no', 'avg_profit', 'total_markets'],
        ascending=[True, False, False, False]
    )

    # Save to CSV
    output_file = 'subcategory_timing_price_recency_analysis.csv'
    results_df.to_csv(output_file, index=False)

    print(f"✅ Saved {len(results_df):,} combinations to {output_file}")
    print()

    # Show comparison
    print("=" * 100)
    print("RECENCY COMPARISON")
    print("=" * 100)
    print()

    for period in ['old', 'recent']:
        period_df = results_df[results_df['period'] == period]
        profitable_df = period_df[period_df['profitable_yes_no'] == 'yes']

        print(f"📊 {period.upper()} (before Jan 2025)" if period == 'old' else f"📊 {period.upper()} (Jan 2025+)")
        print(f"   Total combinations: {len(period_df):,}")
        print(f"   Profitable: {len(profitable_df):,} ({len(profitable_df)/len(period_df)*100:.1f}%)")

        if len(profitable_df) > 0:
            print(f"   Top 5 by avg profit:")
            for idx, row in profitable_df.head(5).iterrows():
                print(f"     - {row['sub_category']} | {row['series_ticker']}")
                print(f"       {row['time_bucket']} | {row['price_bucket']} | "
                      f"{row['total_markets']} markets | {row['accuracy']:.1f}% accuracy | {row['avg_profit']:+.2f}¢")
        print()

    print("=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)

    return results_df


if __name__ == "__main__":
    analyze_with_recency()
