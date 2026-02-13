"""
Comprehensive timing analysis for ALL sub-categories with 20+ markets.
Price range: 90-92¢
Time buckets: 0-25%, 25-50%, 50-75%, 75-100% time elapsed
Profitable threshold: >91% accuracy

Using time-to-close as proxy for time elapsed:
- 75-100% elapsed (LATE): 0-3h to close
- 50-75% elapsed (MID-LATE): 3-12h to close
- 25-50% elapsed (MID-EARLY): 12-48h to close
- 0-25% elapsed (EARLY): 48h+ to close
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_time_elapsed_bucket(hours_to_close):
    """Map time-to-close to time-elapsed bucket."""
    if pd.isna(hours_to_close) or hours_to_close < 0:
        return None
    elif hours_to_close < 3:
        return '75-100%'  # Late in event
    elif hours_to_close < 12:
        return '50-75%'   # Mid-late
    elif hours_to_close < 48:
        return '25-50%'   # Mid-early
    else:
        return '0-25%'    # Early

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

    # Parse timestamps and calculate time to close
    print("Calculating time-to-close...")
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')
    df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

    # Filter for 90-92¢ price range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-92¢ range: {len(price_df):,}")

    # Add time bucket
    price_df['Time_Bucket'] = price_df['Time_To_Close_Hours'].apply(get_time_elapsed_bucket)

    # Filter out markets with unknown timing
    price_df = price_df[price_df['Time_Bucket'].notna()]

    print(f"Markets with valid timing: {len(price_df):,}")

    # Group by sub-category
    subcategory_counts = price_df.groupby('Hierarchical_Path').size().reset_index(name='total')
    eligible_paths = set(subcategory_counts[subcategory_counts['total'] >= 20]['Hierarchical_Path'].values)

    print(f"Sub-categories with 20+ markets: {len(eligible_paths)}")
    print()

    # Filter to eligible sub-categories
    analysis_df = price_df[price_df['Hierarchical_Path'].isin(eligible_paths)].copy()

    # Calculate results for each sub-category
    results = []
    sample_tickers = []

    time_buckets = ['0-25%', '25-50%', '50-75%', '75-100%']

    for path in sorted(eligible_paths):
        path_df = analysis_df[analysis_df['Hierarchical_Path'] == path]

        row_data = {'sub_category': path}

        for bucket in time_buckets:
            bucket_df = path_df[path_df['Time_Bucket'] == bucket]

            total = len(bucket_df)
            if total > 0:
                wins = (bucket_df['Prediction Correct'] == 'CORRECT').sum()
                accuracy = (wins / total) * 100
                profitable = 'PROFITABLE' if accuracy > 91 else 'NOT'

                row_data[f'markets_{bucket}'] = total
                row_data[f'accuracy_{bucket}'] = round(accuracy, 1)
                row_data[f'status_{bucket}'] = profitable

                # Collect sample tickers (up to 3)
                samples = bucket_df['Ticker'].head(3).tolist()
                for idx, ticker in enumerate(samples, 1):
                    sample_tickers.append({
                        'sub_category': path,
                        'time_bucket': bucket,
                        'sample_num': idx,
                        'ticker': ticker,
                        'price': bucket_df[bucket_df['Ticker'] == ticker]['First Touch Price (¢)'].iloc[0],
                        'time_to_close_h': round(bucket_df[bucket_df['Ticker'] == ticker]['Time_To_Close_Hours'].iloc[0], 1),
                        'correct': bucket_df[bucket_df['Ticker'] == ticker]['Prediction Correct'].iloc[0]
                    })
            else:
                row_data[f'markets_{bucket}'] = 0
                row_data[f'accuracy_{bucket}'] = None
                row_data[f'status_{bucket}'] = 'N/A'

        results.append(row_data)

    # Create DataFrames
    results_df = pd.DataFrame(results)
    samples_df = pd.DataFrame(sample_tickers)

    # Reorder columns for main results
    main_cols = ['sub_category']
    for bucket in time_buckets:
        main_cols.extend([f'markets_{bucket}', f'accuracy_{bucket}', f'status_{bucket}'])

    results_df = results_df[main_cols]

    # Save to CSV
    results_df.to_csv('timing_analysis_all_subcategories.csv', index=False)
    samples_df.to_csv('timing_analysis_sample_tickers.csv', index=False)

    print("=" * 150)
    print("TIMING ANALYSIS: ALL SUB-CATEGORIES (90-92¢ ENTRY PRICE)")
    print("Sorted by sub-category name | Profitable threshold: >91% accuracy")
    print("=" * 150)
    print()

    print("Time bucket mapping (using time-to-close as proxy):")
    print("  0-25% time elapsed (EARLY): 48h+ to close")
    print("  25-50% time elapsed (MID-EARLY): 12-48h to close")
    print("  50-75% time elapsed (MID-LATE): 3-12h to close")
    print("  75-100% time elapsed (LATE): 0-3h to close")
    print()
    print("=" * 150)
    print()

    # Display results in a readable table format
    for idx, row in results_df.iterrows():
        print(f"\n{row['sub_category']}")
        print("-" * 150)

        header = f"{'Time Bucket':<20} {'Markets':>10} {'Accuracy':>12} {'Status':>15}"
        print(header)
        print("-" * 150)

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
    print("=" * 150)
    print(f"✅ Saved full results to timing_analysis_all_subcategories.csv ({len(results_df)} sub-categories)")
    print(f"✅ Saved sample tickers to timing_analysis_sample_tickers.csv ({len(samples_df)} samples)")
    print("=" * 150)
    print()

    # Summary statistics
    print("SUMMARY STATISTICS")
    print("-" * 150)

    for bucket in time_buckets:
        bucket_data = results_df[results_df[f'markets_{bucket}'] > 0]

        if len(bucket_data) > 0:
            total_subcats = len(bucket_data)
            profitable_subcats = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<20} {total_subcats} sub-categories | {profitable_subcats} profitable | Avg accuracy: {avg_accuracy:.1f}%")

    print()

if __name__ == "__main__":
    main()
