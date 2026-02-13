"""
Timing analysis: When in a market's life did it cross 90¢, and what was the accuracy?

For each market:
- open_time = close_time - betting_window
- first_touch_pct = (first_touch_time - open_time) / (close_time - open_time) * 100
- Bucket by first_touch_pct: 0-25%, 25-50%, 50-75%, 75-100%

Question: Do markets that cross 90¢ EARLY (0-25% elapsed) settle correctly as often
as markets that cross 90¢ LATE (75-100% elapsed)?

Early crossers that settle correctly are most valuable: early entry + good price + win.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_first_touch_pct_bucket(pct):
    """Bucket by % of market life elapsed when it first touched 90¢."""
    if pd.isna(pct):
        return None
    elif pct < 0 or pct > 100:
        return None  # Invalid
    elif pct <= 25:
        return '0-25%'
    elif pct <= 50:
        return '25-50%'
    elif pct <= 75:
        return '50-75%'
    else:
        return '75-100%'

def main():
    print("Loading data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Map to sub-categories
    print("Mapping to sub-categories...")
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

    # Parse timestamps
    print("Calculating market timing...")
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')

    # Calculate open time from betting window
    df['Betting_Window_Hours'] = df['Betting Window (sec)'] / 3600
    df['Open_DT'] = df['Close_DT'] - pd.to_timedelta(df['Betting_Window_Hours'], unit='h')

    # Calculate when in market's life it first touched 90¢
    df['Market_Duration_Hours'] = (df['Close_DT'] - df['Open_DT']).dt.total_seconds() / 3600
    df['Time_Elapsed_At_First_Touch'] = (df['First_Touch_DT'] - df['Open_DT']).dt.total_seconds() / 3600
    df['First_Touch_Pct'] = (df['Time_Elapsed_At_First_Touch'] / df['Market_Duration_Hours']) * 100

    # Filter for 90-92¢ at first touch
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-92¢ range: {len(price_df):,}")

    # Add timing bucket
    price_df['Timing_Bucket'] = price_df['First_Touch_Pct'].apply(get_first_touch_pct_bucket)

    # Filter out invalid timing
    price_df = price_df[price_df['Timing_Bucket'].notna()]

    print(f"Markets with valid timing: {len(price_df):,}")

    # Group by sub-category
    subcategory_counts = price_df.groupby('Hierarchical_Path').size().reset_index(name='total')
    eligible_paths = set(subcategory_counts[subcategory_counts['total'] >= 20]['Hierarchical_Path'].values)

    print(f"Sub-categories with 20+ markets: {len(eligible_paths)}")
    print()

    # Filter to eligible sub-categories
    analysis_df = price_df[price_df['Hierarchical_Path'].isin(eligible_paths)].copy()

    # Calculate results
    results = []
    sample_tickers = []

    time_buckets = ['0-25%', '25-50%', '50-75%', '75-100%']

    for path in sorted(eligible_paths):
        path_df = analysis_df[analysis_df['Hierarchical_Path'] == path]

        total_markets = len(path_df)
        row_data = {
            'sub_category': path,
            'total_markets': total_markets
        }

        for bucket in time_buckets:
            bucket_df = path_df[path_df['Timing_Bucket'] == bucket]

            count = len(bucket_df)
            if count > 0:
                wins = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
                accuracy = (wins / count) * 100
                status = 'PROFITABLE' if accuracy > 91 else 'NOT'

                row_data[f'markets_{bucket}'] = count
                row_data[f'accuracy_{bucket}'] = round(accuracy, 1)
                row_data[f'status_{bucket}'] = status

                # Sample tickers (up to 3)
                samples = bucket_df.head(3)
                for idx, (_, sample_row) in enumerate(samples.iterrows(), 1):
                    sample_tickers.append({
                        'sub_category': path,
                        'time_bucket': bucket,
                        'sample_num': idx,
                        'ticker': sample_row['Ticker'],
                        'first_touch_price': sample_row['First Touch Price (¢)'],
                        'first_touch_pct': round(sample_row['First_Touch_Pct'], 1),
                        'market_duration_h': round(sample_row['Market_Duration_Hours'], 1),
                        'correct': sample_row['Prediction Correct']
                    })
            else:
                row_data[f'markets_{bucket}'] = 0
                row_data[f'accuracy_{bucket}'] = None
                row_data[f'status_{bucket}'] = 'N/A'

        results.append(row_data)

    # Create DataFrames
    results_df = pd.DataFrame(results)
    samples_df = pd.DataFrame(sample_tickers)

    # Reorder columns
    main_cols = ['sub_category', 'total_markets']
    for bucket in time_buckets:
        main_cols.extend([f'markets_{bucket}', f'accuracy_{bucket}', f'status_{bucket}'])

    results_df = results_df[main_cols]

    # Save to CSV
    results_df.to_csv('timing_by_first_touch_pct.csv', index=False)
    samples_df.to_csv('timing_by_first_touch_pct_samples.csv', index=False)

    print("=" * 160)
    print("TIMING ANALYSIS: When in market's life did it cross 90¢?")
    print("Price: 90-92¢ | Profitable threshold: >91% accuracy")
    print("=" * 160)
    print()

    print("INTERPRETATION:")
    print("  0-25%  = Market crossed 90¢ EARLY in its life (most time remaining)")
    print("  25-50% = Market crossed 90¢ MID-EARLY")
    print("  50-75% = Market crossed 90¢ MID-LATE")
    print("  75-100% = Market crossed 90¢ LATE in its life (near settlement)")
    print()
    print("VALUE: Markets that cross 90¢ early (0-25%) and settle correctly are MOST VALUABLE")
    print("       → You get early entry + good price + win")
    print()
    print("=" * 160)
    print()

    # Display table
    for idx, row in results_df.iterrows():
        print(f"\n{row['sub_category']}")
        print(f"Total markets in sub-category: {row['total_markets']}")
        print("-" * 160)

        header = f"{'When crossed 90¢':<20} {'Markets':>10} {'Accuracy':>12} {'Status':>15}"
        print(header)
        print("-" * 160)

        for bucket in time_buckets:
            markets = row[f'markets_{bucket}']
            accuracy = row[f'accuracy_{bucket}']
            status = row[f'status_{bucket}']

            if markets > 0:
                acc_str = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
                print(f"{bucket:<20} {markets:>10} {acc_str:>12} {status:>15}")
            else:
                print(f"{bucket:<20} {markets:>10} {'N/A':>12} {status:>15}")

    print()
    print("=" * 160)
    print(f"✅ Saved results to timing_by_first_touch_pct.csv ({len(results_df)} sub-categories)")
    print(f"✅ Saved samples to timing_by_first_touch_pct_samples.csv ({len(samples_df)} samples)")
    print("=" * 160)
    print()

    # Summary statistics
    print("SUMMARY: Which timing produces most profitable outcomes?")
    print("-" * 160)

    for bucket in time_buckets:
        bucket_data = results_df[results_df[f'markets_{bucket}'] > 0]

        if len(bucket_data) > 0:
            total_subcats = len(bucket_data)
            profitable_subcats = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            total_markets = bucket_data[f'markets_{bucket}'].sum()
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<15} {total_markets:>6} markets | {total_subcats:>3} sub-categories | "
                  f"{profitable_subcats:>3} profitable | Avg accuracy: {avg_accuracy:.1f}%")

    print()

    # Find sub-categories profitable at EARLY timing (0-25%)
    print("=" * 160)
    print("🎯 SUB-CATEGORIES PROFITABLE AT EARLY TIMING (0-25%) with 10+ markets")
    print("These are the most valuable: early entry + good price + high win rate")
    print("=" * 160)
    print()

    early_profitable = results_df[
        (results_df['status_0-25%'] == 'PROFITABLE') &
        (results_df['markets_0-25%'] >= 10)
    ].sort_values('accuracy_0-25%', ascending=False)

    if len(early_profitable) > 0:
        print(f"{'Sub-Category':<70} {'Markets':>10} {'Accuracy':>12}")
        print("-" * 160)
        for idx, row in early_profitable.iterrows():
            print(f"{row['sub_category']:<70} {row['markets_0-25%']:>10} {row['accuracy_0-25%']:>11.1f}%")
    else:
        print("None found with 10+ markets")

    print()

if __name__ == "__main__":
    main()
