"""
Timing analysis by SERIES TICKER using ESTIMATED open times.

This uses ticker-based open_time estimates to preserve ALL markets
instead of losing 25.9% to missing API data.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_first_touch_pct_bucket(pct):
    """Bucket by % of market life elapsed when it first touched 90¢."""
    if pd.isna(pct):
        return None
    elif pct < 0:
        return 'NEGATIVE'
    elif pct > 100:
        return 'OVER_100'
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
    print("TIMING ANALYSIS BY SERIES TICKER (ESTIMATED OPEN TIMES)")
    print("=" * 100)
    print()

    # Load data with estimated open times
    print("Loading data with estimated open times...")
    df = pd.read_csv('comprehensive_with_estimated_open_times.csv')

    print(f"  Loaded {len(df):,} markets")
    print()

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

    # Filter for 90-92¢
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-92¢ range: {len(price_df):,}")

    # Add timing bucket
    price_df['Timing_Bucket'] = price_df['First_Touch_Pct'].apply(get_first_touch_pct_bucket)

    # Filter to valid timing
    valid_df = price_df[price_df['Timing_Bucket'].isin(['0-25%', '25-50%', '50-75%', '75-100%'])].copy()
    print(f"Markets with valid timing: {len(valid_df):,}")
    print()

    # Show data quality
    print("Data quality:")
    print(f"  Valid (0-100%): {len(valid_df):,} ({len(valid_df)/len(price_df)*100:.1f}%)")
    print(f"  Negative: {(price_df['Timing_Bucket'] == 'NEGATIVE').sum():,}")
    print(f"  Over 100%: {(price_df['Timing_Bucket'] == 'OVER_100').sum():,}")
    print()

    # Find series tickers with 20+ markets
    ticker_counts = valid_df.groupby('Series Ticker').size().reset_index(name='total')
    eligible_tickers = set(ticker_counts[ticker_counts['total'] >= 20]['Series Ticker'].values)

    print(f"Series tickers with 20+ markets: {len(eligible_tickers)}")
    print()

    # Filter to eligible tickers
    analysis_df = valid_df[valid_df['Series Ticker'].isin(eligible_tickers)].copy()

    print(f"Total markets in analysis: {len(analysis_df):,}")
    print()

    # Calculate results
    results = []
    time_buckets = ['0-25%', '25-50%', '50-75%', '75-100%']

    for ticker in sorted(eligible_tickers):
        ticker_df = analysis_df[analysis_df['Series Ticker'] == ticker]

        total_markets = len(ticker_df)

        # Get category info (use most common)
        category = ticker_df['Hierarchical_Path'].mode()[0] if len(ticker_df) > 0 else ''

        row_data = {
            'series_ticker': ticker,
            'sub_category': category,
            'total_markets': total_markets
        }

        for bucket in time_buckets:
            bucket_df = ticker_df[ticker_df['Timing_Bucket'] == bucket]

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
    main_cols = ['series_ticker', 'sub_category', 'total_markets']
    for bucket in time_buckets:
        main_cols.extend([f'markets_{bucket}', f'accuracy_{bucket}', f'status_{bucket}'])

    results_df = results_df[main_cols]

    # Save to CSV
    results_df.to_csv('timing_by_series_ticker_estimated.csv', index=False)

    print("=" * 140)
    print("RESULTS SAVED")
    print("=" * 140)
    print(f"✅ Saved to timing_by_series_ticker_estimated.csv ({len(results_df)} series tickers)")
    print()

    # Summary by timing bucket
    print("=" * 140)
    print("SUMMARY: Which timing produces most profitable outcomes?")
    print("=" * 140)
    print()

    print(f"{'Timing':<15} {'Total Markets':>15} {'Series Tickers':>18} {'Profitable':>15} {'Avg Accuracy':>15}")
    print("-" * 140)

    for bucket in time_buckets:
        bucket_data = results_df[results_df[f'markets_{bucket}'] > 0]

        if len(bucket_data) > 0:
            total_tickers = len(bucket_data)
            profitable_tickers = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            total_markets = bucket_data[f'markets_{bucket}'].sum()
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<15} {total_markets:>15,} {total_tickers:>18} {profitable_tickers:>15} {avg_accuracy:>14.1f}%")

    print()

    # Best early opportunities
    print("=" * 140)
    print("🎯 BEST OPPORTUNITIES: Series tickers profitable in EARLY timing (0-25%) with 10+ markets")
    print("=" * 140)
    print()

    early_profitable = results_df[
        (results_df['status_0-25%'] == 'PROFITABLE') &
        (results_df['markets_0-25%'] >= 10)
    ].sort_values('accuracy_0-25%', ascending=False)

    if len(early_profitable) > 0:
        print(f"{'Series Ticker':<30} {'Sub-Category':<50} {'Markets':>10} {'Accuracy':>12}")
        print("-" * 140)
        for idx, row in early_profitable.iterrows():
            print(f"{row['series_ticker']:<30} {row['sub_category']:<50} {row['markets_0-25%']:>10} {row['accuracy_0-25%']:>11.1f}%")
    else:
        print("None found")

    print()

    # Show NBA breakdown
    print("=" * 140)
    print("🏀 NBA BREAKDOWN BY SERIES TICKER (with estimated open times)")
    print("=" * 140)
    print()

    nba_tickers = results_df[results_df['sub_category'].str.contains('NBA', na=False)]

    if len(nba_tickers) > 0:
        print(f"{'Series Ticker':<30} {'Total':>8} {'0-25%':>8} {'Acc%':>7} {'25-50%':>8} {'Acc%':>7} "
              f"{'50-75%':>8} {'Acc%':>7} {'75-100%':>8} {'Acc%':>7}")
        print("-" * 140)

        for idx, row in nba_tickers.iterrows():
            acc_0_25 = f"{row['accuracy_0-25%']:.1f}" if row['accuracy_0-25%'] else "N/A"
            acc_25_50 = f"{row['accuracy_25-50%']:.1f}" if row['accuracy_25-50%'] else "N/A"
            acc_50_75 = f"{row['accuracy_50-75%']:.1f}" if row['accuracy_50-75%'] else "N/A"
            acc_75_100 = f"{row['accuracy_75-100%']:.1f}" if row['accuracy_75-100%'] else "N/A"

            print(f"{row['series_ticker']:<30} {row['total_markets']:>8} "
                  f"{row['markets_0-25%']:>8} {acc_0_25:>7} "
                  f"{row['markets_25-50%']:>8} {acc_25_50:>7} "
                  f"{row['markets_50-75%']:>8} {acc_50_75:>7} "
                  f"{row['markets_75-100%']:>8} {acc_75_100:>7}")

        print()
        print(f"Total NBA markets in analysis: {nba_tickers['total_markets'].sum():,}")
    else:
        print("No NBA series tickers found with 20+ markets")

    print()

    # Compare API vs Estimated
    print("=" * 140)
    print("COMPARISON: API-based vs Estimated open times")
    print("=" * 140)
    print()
    print("API-based approach:")
    print("  - Lost 2,615 markets (25.9%) due to missing API data")
    print("  - NBA: Only 32 markets (lost 763 markets, 96% loss!)")
    print("  - Final: 7,160 markets")
    print()
    print("Estimated approach:")
    print(f"  - Markets analyzed: {len(analysis_df):,}")
    print(f"  - NBA markets: {nba_tickers['total_markets'].sum() if len(nba_tickers) > 0 else 0:,}")
    print(f"  - Data retention: Much better!")
    print()

if __name__ == "__main__":
    main()
