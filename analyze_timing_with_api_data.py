"""
Timing analysis using API data for open_time.

Calculate first_touch_pct = (first_touch_time - open_time) / (close_time - open_time)
Bucket by: 0-25%, 25-50%, 50-75%, 75-100%
Analyze accuracy by sub-category and timing bucket.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_first_touch_pct_bucket(pct):
    """Bucket by % of market life elapsed when it first touched 90¢."""
    if pd.isna(pct):
        return None
    elif pct < 0:
        return 'NEGATIVE'  # First touch before market opened (data error)
    elif pct > 100:
        return 'OVER_100'  # First touch after market closed (data error)
    elif pct <= 25:
        return '0-25%'
    elif pct <= 50:
        return '25-50%'
    elif pct <= 75:
        return '50-75%'
    else:
        return '75-100%'

def main():
    print("=" * 100)
    print("TIMING ANALYSIS: When in market's life did it first cross 90¢?")
    print("=" * 100)
    print()

    # Load data
    print("Loading comprehensive CSV...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
    print(f"  Loaded {len(df):,} markets")

    print("Loading API market times...")
    api_df = pd.read_csv('market_open_close_times_for_analysis.csv')
    print(f"  Loaded {len(api_df):,} markets with open/close times")
    print()

    # Parse timestamps from CSV
    print("Parsing timestamps...")
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['CSV_Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')

    # Parse timestamps from API
    api_df['API_Open_DT'] = pd.to_datetime(api_df['open_time'], format='ISO8601')
    api_df['API_Close_DT'] = pd.to_datetime(api_df['close_time'], format='ISO8601')

    # Merge on ticker
    print("Merging CSV with API data...")
    merged = df.merge(
        api_df[['ticker', 'API_Open_DT', 'API_Close_DT']],
        left_on='Ticker',
        right_on='ticker',
        how='left'
    )

    print(f"  After merge: {len(merged):,} markets")
    print(f"  Markets with API open_time: {merged['API_Open_DT'].notna().sum():,}")
    print()

    # Calculate market timing
    print("Calculating first_touch_pct...")
    merged['Market_Duration_Hours'] = (merged['API_Close_DT'] - merged['API_Open_DT']).dt.total_seconds() / 3600
    merged['Time_Elapsed_At_First_Touch'] = (merged['First_Touch_DT'] - merged['API_Open_DT']).dt.total_seconds() / 3600
    merged['First_Touch_Pct'] = (merged['Time_Elapsed_At_First_Touch'] / merged['Market_Duration_Hours']) * 100

    # Map to sub-categories
    print("Mapping to sub-categories...")
    merged['Sub_Category'] = merged.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[0],
        axis=1
    )
    merged['Sub_Sub_Category'] = merged.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[1],
        axis=1
    )
    merged['Hierarchical_Path'] = merged.apply(
        lambda row: f"{row['Category']} > {row['Sub_Category']}" if pd.isna(row['Sub_Sub_Category'])
                    else f"{row['Category']} > {row['Sub_Category']} > {row['Sub_Sub_Category']}",
        axis=1
    )

    # Filter for 90-92¢ at first touch
    print("Filtering for 90-92¢ price range...")
    price_df = merged[
        (merged['First Touch Price (¢)'] >= 90) &
        (merged['First Touch Price (¢)'] < 93)
    ].copy()
    print(f"  Markets in 90-92¢ range: {len(price_df):,}")

    # Add timing bucket
    price_df['Timing_Bucket'] = price_df['First_Touch_Pct'].apply(get_first_touch_pct_bucket)

    # Filter to valid timing (0-100%)
    valid_df = price_df[price_df['Timing_Bucket'].isin(['0-25%', '25-50%', '50-75%', '75-100%'])].copy()
    print(f"  Markets with valid timing (0-100%): {len(valid_df):,}")

    # Show data quality stats
    print()
    print("Data quality:")
    print(f"  Negative timing (first touch before open): {(price_df['Timing_Bucket'] == 'NEGATIVE').sum():,}")
    print(f"  Over 100% (first touch after close): {(price_df['Timing_Bucket'] == 'OVER_100').sum():,}")
    print(f"  Missing timing: {price_df['Timing_Bucket'].isna().sum():,}")
    print()

    # Find sub-categories with 20+ markets
    subcategory_counts = valid_df.groupby('Hierarchical_Path').size().reset_index(name='total')
    eligible_paths = set(subcategory_counts[subcategory_counts['total'] >= 20]['Hierarchical_Path'].values)

    print(f"Sub-categories with 20+ markets: {len(eligible_paths)}")
    print()

    # Filter to eligible sub-categories
    analysis_df = valid_df[valid_df['Hierarchical_Path'].isin(eligible_paths)].copy()

    # Calculate results
    results = []
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
            else:
                row_data[f'markets_{bucket}'] = 0
                row_data[f'accuracy_{bucket}'] = None
                row_data[f'status_{bucket}'] = 'N/A'

        results.append(row_data)

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Reorder columns
    main_cols = ['sub_category', 'total_markets']
    for bucket in time_buckets:
        main_cols.extend([f'markets_{bucket}', f'accuracy_{bucket}', f'status_{bucket}'])

    results_df = results_df[main_cols]

    # Save to CSV
    results_df.to_csv('timing_by_first_touch_pct_api.csv', index=False)

    print("=" * 140)
    print("RESULTS: Accuracy by timing of first 90¢ cross")
    print("Price: 90-92¢ | Profitable threshold: >91% accuracy")
    print("=" * 140)
    print()

    print("INTERPRETATION:")
    print("  0-25%  = Market crossed 90¢ in FIRST QUARTER of its life (most valuable if profitable)")
    print("  25-50% = Market crossed 90¢ in SECOND QUARTER")
    print("  50-75% = Market crossed 90¢ in THIRD QUARTER")
    print("  75-100% = Market crossed 90¢ in FINAL QUARTER (near settlement)")
    print()
    print("KEY INSIGHT: Early crossers (0-25%) that are profitable = best opportunities")
    print("             → Early entry + good price + high win rate")
    print()
    print("=" * 140)
    print()

    # Display table
    for idx, row in results_df.iterrows():
        print(f"\n{row['sub_category']}")
        print(f"Total markets: {row['total_markets']}")
        print("-" * 140)

        header = f"{'Timing':<15} {'Markets':>10} {'Accuracy':>12} {'Status':>15}"
        print(header)
        print("-" * 140)

        for bucket in time_buckets:
            markets = row[f'markets_{bucket}']
            accuracy = row[f'accuracy_{bucket}']
            status = row[f'status_{bucket}']

            if markets > 0:
                acc_str = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
                print(f"{bucket:<15} {markets:>10} {acc_str:>12} {status:>15}")
            else:
                print(f"{bucket:<15} {markets:>10} {'N/A':>12} {status:>15}")

    print()
    print("=" * 140)
    print(f"✅ Saved results to timing_by_first_touch_pct_api.csv ({len(results_df)} sub-categories)")
    print("=" * 140)
    print()

    # Summary statistics
    print("SUMMARY: Which timing produces most profitable outcomes?")
    print("-" * 140)

    summary_header = f"{'Timing':<15} {'Total Markets':>15} {'Sub-Categories':>18} {'Profitable':>15} {'Avg Accuracy':>15}"
    print(summary_header)
    print("-" * 140)

    for bucket in time_buckets:
        bucket_data = results_df[results_df[f'markets_{bucket}'] > 0]

        if len(bucket_data) > 0:
            total_subcats = len(bucket_data)
            profitable_subcats = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            total_markets = bucket_data[f'markets_{bucket}'].sum()
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<15} {total_markets:>15,} {total_subcats:>18} {profitable_subcats:>15} {avg_accuracy:>14.1f}%")

    print()

    # Find sub-categories profitable at EARLY timing (0-25%) with 10+ markets
    print("=" * 140)
    print("🎯 BEST OPPORTUNITIES: Sub-categories profitable in EARLY timing (0-25%) with 10+ markets")
    print("These markets cross 90¢ early AND settle correctly = ideal for early entry")
    print("=" * 140)
    print()

    early_profitable = results_df[
        (results_df['status_0-25%'] == 'PROFITABLE') &
        (results_df['markets_0-25%'] >= 10)
    ].sort_values('accuracy_0-25%', ascending=False)

    if len(early_profitable) > 0:
        print(f"{'Sub-Category':<80} {'Markets':>10} {'Accuracy':>12}")
        print("-" * 140)
        for idx, row in early_profitable.iterrows():
            print(f"{row['sub_category']:<80} {row['markets_0-25%']:>10} {row['accuracy_0-25%']:>11.1f}%")
    else:
        print("None found with 10+ markets")

    print()

    # Find sub-categories profitable ONLY late (75-100%) but not early
    print("=" * 140)
    print("⚠️  LATE BLOOMERS: Sub-categories only profitable in LATE timing (75-100%)")
    print("These require waiting until near settlement - less valuable")
    print("=" * 140)
    print()

    late_only = results_df[
        (results_df['status_75-100%'] == 'PROFITABLE') &
        (results_df['status_0-25%'] == 'NOT') &
        (results_df['markets_75-100%'] >= 10) &
        (results_df['markets_0-25%'] >= 10)
    ].sort_values('accuracy_75-100%', ascending=False)

    if len(late_only) > 0:
        print(f"{'Sub-Category':<70} {'Early (0-25%)':>18} {'Late (75-100%)':>18}")
        print("-" * 140)
        for idx, row in late_only.iterrows():
            early_acc = f"{row['accuracy_0-25%']:.1f}%" if row['accuracy_0-25%'] else "N/A"
            late_acc = f"{row['accuracy_75-100%']:.1f}%" if row['accuracy_75-100%'] else "N/A"
            print(f"{row['sub_category']:<70} {early_acc:>18} {late_acc:>18}")
    else:
        print("None found")

    print()

if __name__ == "__main__":
    main()
