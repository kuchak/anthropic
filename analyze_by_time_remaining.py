"""
Time-remaining analysis: How accurate is betting at 90¢ based on TIME LEFT until close?

NO need for open_time! Just calculate:
1. time_remaining_first = close_time - first_touch_time
2. time_remaining_permanent = close_time - permanent_cross_time

Buckets: 0-15min, 15-60min, 1-3hrs, 3hrs+

Shows:
- First touch: If bot bets immediately when seeing 90¢, how often does it win?
- Permanent cross: How often does price drop back below 90¢ before settling?
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_time_bucket(minutes):
    """Bucket by absolute time remaining until close."""
    if pd.isna(minutes):
        return None
    elif minutes < 0:
        return 'NEGATIVE'
    elif minutes <= 15:
        return '0-15min'
    elif minutes <= 60:
        return '15-60min'
    elif minutes <= 180:  # 3 hours
        return '1-3hrs'
    else:
        return '3hrs+'

def main():
    print("=" * 100)
    print("TIME-REMAINING ANALYSIS: How accurate is 90¢ betting by TIME LEFT until close?")
    print("=" * 100)
    print()

    # Load data
    print("Loading data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
    print(f"  Loaded {len(df):,} markets")
    print()

    # Parse timestamps
    print("Parsing timestamps...")
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['Permanent_Cross_DT'] = pd.to_datetime(df['Permanent Cross Time'], format='ISO8601')
    df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')

    # Calculate time remaining (in minutes)
    df['Time_Remaining_First_Min'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 60
    df['Time_Remaining_Permanent_Min'] = (df['Close_DT'] - df['Permanent_Cross_DT']).dt.total_seconds() / 60

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
    print()

    # Add time buckets
    price_df['Time_Bucket_First'] = price_df['Time_Remaining_First_Min'].apply(get_time_bucket)
    price_df['Time_Bucket_Permanent'] = price_df['Time_Remaining_Permanent_Min'].apply(get_time_bucket)

    # Filter to valid (non-negative)
    valid_buckets = ['0-15min', '15-60min', '1-3hrs', '3hrs+']
    valid_first = price_df[price_df['Time_Bucket_First'].isin(valid_buckets)].copy()
    valid_perm = price_df[price_df['Time_Bucket_Permanent'].isin(valid_buckets)].copy()

    print(f"Valid markets (first touch): {len(valid_first):,}")
    print(f"Valid markets (permanent cross): {len(valid_perm):,}")
    print()

    # Find series tickers with 20+ markets
    ticker_counts = valid_first.groupby('Series Ticker').size().reset_index(name='total')
    eligible_tickers = set(ticker_counts[ticker_counts['total'] >= 20]['Series Ticker'].values)

    print(f"Series tickers with 20+ markets: {len(eligible_tickers)}")
    print()

    # ======================
    # FIRST TOUCH ANALYSIS
    # ======================
    print("Analyzing FIRST TOUCH timing...")
    first_results = []

    for ticker in sorted(eligible_tickers):
        ticker_df = valid_first[valid_first['Series Ticker'] == ticker]
        total_markets = len(ticker_df)
        category = ticker_df['Hierarchical_Path'].mode()[0] if len(ticker_df) > 0 else ''

        row_data = {
            'series_ticker': ticker,
            'sub_category': category,
            'total_markets': total_markets
        }

        for bucket in valid_buckets:
            bucket_df = ticker_df[ticker_df['Time_Bucket_First'] == bucket]
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

        first_results.append(row_data)

    first_df = pd.DataFrame(first_results)

    # Reorder columns
    main_cols = ['series_ticker', 'sub_category', 'total_markets']
    for bucket in valid_buckets:
        main_cols.extend([f'markets_{bucket}', f'accuracy_{bucket}', f'status_{bucket}'])
    first_df = first_df[main_cols]

    # Save
    first_df.to_csv('timing_by_time_remaining_first_touch.csv', index=False)

    # ======================
    # PERMANENT CROSS ANALYSIS
    # ======================
    print("Analyzing PERMANENT CROSS timing...")
    perm_results = []

    for ticker in sorted(eligible_tickers):
        ticker_df = valid_perm[valid_perm['Series Ticker'] == ticker]
        total_markets = len(ticker_df)
        category = ticker_df['Hierarchical_Path'].mode()[0] if len(ticker_df) > 0 else ''

        row_data = {
            'series_ticker': ticker,
            'sub_category': category,
            'total_markets': total_markets
        }

        for bucket in valid_buckets:
            bucket_df = ticker_df[ticker_df['Time_Bucket_Permanent'] == bucket]
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

        perm_results.append(row_data)

    perm_df = pd.DataFrame(perm_results)
    perm_df = perm_df[main_cols]

    # Save
    perm_df.to_csv('timing_by_time_remaining_permanent_cross.csv', index=False)

    print()
    print("=" * 140)
    print("RESULTS SAVED")
    print("=" * 140)
    print(f"✅ First touch: timing_by_time_remaining_first_touch.csv ({len(first_df)} tickers)")
    print(f"✅ Permanent cross: timing_by_time_remaining_permanent_cross.csv ({len(perm_df)} tickers)")
    print()

    # Summary
    print("=" * 140)
    print("SUMMARY: FIRST TOUCH (bet immediately when seeing 90¢)")
    print("=" * 140)
    print()

    print(f"{'Time Remaining':<15} {'Total Markets':>15} {'Tickers':>10} {'Profitable':>12} {'Avg Accuracy':>15}")
    print("-" * 140)

    for bucket in valid_buckets:
        bucket_data = first_df[first_df[f'markets_{bucket}'] > 0]
        if len(bucket_data) > 0:
            total_tickers = len(bucket_data)
            profitable_tickers = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            total_markets = bucket_data[f'markets_{bucket}'].sum()
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<15} {total_markets:>15,} {total_tickers:>10} {profitable_tickers:>12} {avg_accuracy:>14.1f}%")

    print()
    print("=" * 140)
    print("SUMMARY: PERMANENT CROSS (only after price stays above 90¢)")
    print("=" * 140)
    print()

    print(f"{'Time Remaining':<15} {'Total Markets':>15} {'Tickers':>10} {'Profitable':>12} {'Avg Accuracy':>15}")
    print("-" * 140)

    for bucket in valid_buckets:
        bucket_data = perm_df[perm_df[f'markets_{bucket}'] > 0]
        if len(bucket_data) > 0:
            total_tickers = len(bucket_data)
            profitable_tickers = len(bucket_data[bucket_data[f'status_{bucket}'] == 'PROFITABLE'])
            total_markets = bucket_data[f'markets_{bucket}'].sum()
            avg_accuracy = bucket_data[f'accuracy_{bucket}'].mean()

            print(f"{bucket:<15} {total_markets:>15,} {total_tickers:>10} {profitable_tickers:>12} {avg_accuracy:>14.1f}%")

    print()

    # Best opportunities
    print("=" * 140)
    print("🎯 BEST OPPORTUNITIES: 3hrs+ time remaining, >91% accuracy (FIRST TOUCH)")
    print("=" * 140)
    print()

    early_bets = first_df[
        (first_df['status_3hrs+'] == 'PROFITABLE') &
        (first_df['markets_3hrs+'] >= 10)
    ].sort_values('accuracy_3hrs+', ascending=False)

    if len(early_bets) > 0:
        print(f"{'Series Ticker':<30} {'Sub-Category':<50} {'Markets':>10} {'Accuracy':>12}")
        print("-" * 140)
        for idx, row in early_bets.iterrows():
            print(f"{row['series_ticker']:<30} {row['sub_category']:<50} {row['markets_3hrs+']:>10} {row['accuracy_3hrs+']:>11.1f}%")
    else:
        print("None found")

    print()

    # Price stability check
    print("=" * 140)
    print("⚠️  PRICE STABILITY: How often does first touch = permanent cross?")
    print("=" * 140)
    print()

    # Calculate gap between first touch and permanent cross
    price_df['Time_Gap_Min'] = price_df['Time_Remaining_First_Min'] - price_df['Time_Remaining_Permanent_Min']
    price_df['Immediate_Permanent'] = price_df['Time_Gap_Min'] < 1  # Within 1 minute

    stability_rate = (price_df['Immediate_Permanent'].sum() / len(price_df)) * 100
    print(f"Markets where first touch = permanent cross (stable): {stability_rate:.1f}%")
    print(f"Markets where price dropped back (unstable): {100-stability_rate:.1f}%")
    print()
    print("→ Gap between first/permanent shows how often price drops back below 90¢")
    print()

if __name__ == "__main__":
    main()
