"""
Fast local timing + price analysis using existing CSV data only.
NO API calls. Uses time-to-close as proxy for timing.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def parse_timestamp(ts_str):
    """Parse ISO timestamp."""
    if pd.isna(ts_str):
        return None
    try:
        return pd.to_datetime(ts_str, format='ISO8601')
    except:
        return None

def get_time_to_close_bucket(hours):
    """Bucket time remaining until close."""
    if pd.isna(hours) or hours < 0:
        return 'Unknown'
    elif hours < 1:
        return '0-1h'
    elif hours < 3:
        return '1-3h'
    elif hours < 6:
        return '3-6h'
    elif hours < 12:
        return '6-12h'
    elif hours < 24:
        return '12-24h'
    else:
        return '24h+'

def get_price_bucket(price):
    """Bucket price."""
    if pd.isna(price):
        return 'Unknown'
    elif 85 <= price < 90:
        return '85-89¢'
    elif 90 <= price < 93:
        return '90-92¢'
    elif 93 <= price < 96:
        return '93-95¢'
    elif 96 <= price <= 98:
        return '96-98¢'
    else:
        return 'Other'

def analyze_local():
    """Main analysis using local data only."""

    print("=" * 100)
    print("FAST LOCAL TIMING + PRICE ANALYSIS (NO API CALLS)")
    print("Using time-to-close as timing proxy")
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

    # Calculate time to close (in hours)
    print("Calculating time-to-close from existing timestamps...")
    df['First_Touch_DT'] = df['First Touch Time'].apply(parse_timestamp)
    df['Close_DT'] = df['Market Close Time'].apply(parse_timestamp)

    df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

    # Add buckets
    df['Time_Bucket'] = df['Time_To_Close_Hours'].apply(get_time_to_close_bucket)
    df['Price_Bucket'] = df['First Touch Price (¢)'].apply(get_price_bucket)

    # Filter: 50+ markets per sub-category (NO accuracy filter)
    print("Finding sub-categories with 50+ markets...")
    subcategory_counts = df.groupby('Hierarchical_Path').size().reset_index(name='total')
    eligible_paths = set(subcategory_counts[subcategory_counts['total'] >= 50]['Hierarchical_Path'].values)

    print(f"Found {len(eligible_paths)} eligible sub-categories")
    print()

    # Filter data
    analysis_df = df[df['Hierarchical_Path'].isin(eligible_paths)].copy()

    # Filter valid data (exclude Unknown/Other)
    valid_df = analysis_df[
        (analysis_df['Time_Bucket'] != 'Unknown') &
        (analysis_df['Price_Bucket'] != 'Unknown') &
        (analysis_df['Price_Bucket'] != 'Other')
    ].copy()

    print(f"Total markets: {len(analysis_df):,}")
    print(f"Markets with valid timing + price: {len(valid_df):,}")
    print()

    # Calculate profit
    valid_df['Profit'] = valid_df.apply(
        lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
                   else -row['First Touch Price (¢)'],
        axis=1
    )

    # Aggregate by sub-category, series ticker, time bucket, price bucket
    print("Aggregating results...")

    results = []

    for path in sorted(eligible_paths):
        path_df = valid_df[valid_df['Hierarchical_Path'] == path]

        if len(path_df) == 0:
            continue

        series_tickers = path_df['Series Ticker'].unique()

        for series_ticker in series_tickers:
            series_df = path_df[path_df['Series Ticker'] == series_ticker]

            for time_bucket in ['0-1h', '1-3h', '3-6h', '6-12h', '12-24h', '24h+']:
                time_df = series_df[series_df['Time_Bucket'] == time_bucket]

                if len(time_df) == 0:
                    continue

                for price_bucket in ['85-89¢', '90-92¢', '93-95¢', '96-98¢']:
                    bucket_df = time_df[time_df['Price_Bucket'] == price_bucket]

                    if len(bucket_df) == 0:
                        continue

                    total = len(bucket_df)
                    wins = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
                    losses = total - wins
                    accuracy = (wins / total) * 100
                    avg_profit = bucket_df['Profit'].mean()
                    profitable = 'yes' if avg_profit > 0 else 'no'

                    # Get sample tickers (up to 5)
                    sample_tickers = bucket_df['Ticker'].head(5).tolist()

                    results.append({
                        'sub_category': path,
                        'series_ticker': series_ticker,
                        'time_bucket': time_bucket,
                        'price_bucket': price_bucket,
                        'total_markets': total,
                        'wins': wins,
                        'losses': losses,
                        'accuracy': round(accuracy, 1),
                        'avg_profit': round(avg_profit, 2),
                        'total_profit': round(avg_profit * total, 2),
                        'profitable_yes_no': profitable,
                        'sample_tickers': '|'.join(sample_tickers)
                    })

    # Create dataframe
    results_df = pd.DataFrame(results)

    # Sort by total profit (accounts for both avg profit and volume)
    results_df = results_df.sort_values('total_profit', ascending=False)

    # Save to CSV
    output_file = 'timing_price_local_analysis.csv'
    results_df.to_csv(output_file, index=False)

    print(f"✅ Saved {len(results_df):,} combinations to {output_file}")
    print()

    # Show top 30 most profitable
    print("=" * 100)
    print("TOP 30 MOST PROFITABLE TIMING + PRICE COMBINATIONS")
    print("Sorted by total profit (avg_profit × total_markets)")
    print("=" * 100)
    print()

    top30 = results_df.head(30)

    for idx, row in top30.iterrows():
        print(f"\n{idx+1}. {row['sub_category']}")
        print(f"   Series: {row['series_ticker']}")
        print(f"   Timing: {row['time_bucket']} to close | Price: {row['price_bucket']}")
        print(f"   Markets: {row['total_markets']} | Wins: {row['wins']} | Losses: {row['losses']}")
        print(f"   Accuracy: {row['accuracy']:.1f}% | Avg Profit: {row['avg_profit']:+.2f}¢ | Total Profit: {row['total_profit']:+.2f}¢")
        print(f"   Sample Tickers: {row['sample_tickers'][:200]}{'...' if len(row['sample_tickers']) > 200 else ''}")

    print()
    print("=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)

    return results_df


if __name__ == "__main__":
    analyze_local()
