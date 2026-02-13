"""
Calculate optimal waiting period for price stability.

Question: How long should bot wait after first seeing 90¢ before betting?

Analysis:
- For markets where price dropped back (first_touch != permanent_cross)
- Calculate: time_gap = permanent_cross_time - first_touch_time
- Show distribution: median, 25th/75th percentile, mean
- Break down by series ticker to find market-specific patterns
"""

import pandas as pd
import numpy as np
from map_kalshi_subcategories import map_to_subcategory

def main():
    print("=" * 100)
    print("STABILITY WAITING PERIOD ANALYSIS")
    print("How long should bot wait after first seeing 90¢?")
    print("=" * 100)
    print()

    # Load data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
    print(f"Loaded {len(df):,} markets")

    # Parse timestamps
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['Permanent_Cross_DT'] = pd.to_datetime(df['Permanent Cross Time'], format='ISO8601')
    df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')

    # Map to categories
    df['Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[0],
        axis=1
    )

    # Filter for 90-92¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-92¢ range: {len(price_df):,}")
    print()

    # Calculate time gap (in minutes)
    price_df['Time_Gap_Min'] = (price_df['Permanent_Cross_DT'] - price_df['First_Touch_DT']).dt.total_seconds() / 60

    # Classify markets
    price_df['Immediate_Stable'] = price_df['Time_Gap_Min'] < 1  # Within 1 minute
    price_df['Dropped_Back'] = price_df['Time_Gap_Min'] >= 1     # Dropped back below 90¢

    immediate_count = price_df['Immediate_Stable'].sum()
    dropped_count = price_df['Dropped_Back'].sum()

    print("=" * 100)
    print("PRICE STABILITY CLASSIFICATION")
    print("=" * 100)
    print()
    print(f"Immediately stable (gap < 1 min):  {immediate_count:,} markets ({immediate_count/len(price_df)*100:.1f}%)")
    print(f"Dropped back (gap >= 1 min):       {dropped_count:,} markets ({dropped_count/len(price_df)*100:.1f}%)")
    print()

    # Focus on markets that dropped back
    unstable_df = price_df[price_df['Dropped_Back']].copy()

    if len(unstable_df) == 0:
        print("No unstable markets found!")
        return

    print("=" * 100)
    print("TIME GAP DISTRIBUTION (for markets that dropped back)")
    print("=" * 100)
    print()

    # Overall statistics
    print("OVERALL:")
    print(f"  Count:          {len(unstable_df):,} markets")
    print(f"  Mean:           {unstable_df['Time_Gap_Min'].mean():.1f} minutes")
    print(f"  Median:         {unstable_df['Time_Gap_Min'].median():.1f} minutes")
    print(f"  25th percentile: {unstable_df['Time_Gap_Min'].quantile(0.25):.1f} minutes")
    print(f"  75th percentile: {unstable_df['Time_Gap_Min'].quantile(0.75):.1f} minutes")
    print(f"  90th percentile: {unstable_df['Time_Gap_Min'].quantile(0.90):.1f} minutes")
    print(f"  95th percentile: {unstable_df['Time_Gap_Min'].quantile(0.95):.1f} minutes")
    print(f"  Max:            {unstable_df['Time_Gap_Min'].max():.1f} minutes")
    print()

    # Distribution buckets
    print("DISTRIBUTION BY TIME BUCKET:")
    print("-" * 100)
    print(f"{'Time Gap':<20} {'Count':>10} {'Percentage':>12} {'Cumulative':>12}")
    print("-" * 100)

    buckets = [
        ('0-5 min', 0, 5),
        ('5-15 min', 5, 15),
        ('15-30 min', 15, 30),
        ('30-60 min', 30, 60),
        ('1-2 hours', 60, 120),
        ('2-6 hours', 120, 360),
        ('6-24 hours', 360, 1440),
        ('24+ hours', 1440, float('inf'))
    ]

    cumulative = 0
    for label, low, high in buckets:
        count = ((unstable_df['Time_Gap_Min'] >= low) & (unstable_df['Time_Gap_Min'] < high)).sum()
        pct = count / len(unstable_df) * 100
        cumulative += pct
        print(f"{label:<20} {count:>10,} {pct:>11.1f}% {cumulative:>11.1f}%")

    print()

    # By series ticker (for tickers with 20+ dropped-back markets)
    print("=" * 100)
    print("TIME GAP BY SERIES TICKER (tickers with 20+ unstable markets)")
    print("=" * 100)
    print()

    ticker_stats = []
    for ticker in unstable_df['Series Ticker'].unique():
        ticker_df = unstable_df[unstable_df['Series Ticker'] == ticker]

        if len(ticker_df) >= 20:
            category = ticker_df['Sub_Category'].mode()[0] if len(ticker_df) > 0 else ''

            ticker_stats.append({
                'ticker': ticker,
                'category': category,
                'count': len(ticker_df),
                'median_gap': ticker_df['Time_Gap_Min'].median(),
                'p25_gap': ticker_df['Time_Gap_Min'].quantile(0.25),
                'p75_gap': ticker_df['Time_Gap_Min'].quantile(0.75),
                'mean_gap': ticker_df['Time_Gap_Min'].mean()
            })

    ticker_stats_df = pd.DataFrame(ticker_stats).sort_values('median_gap')

    print(f"{'Series Ticker':<30} {'Category':<30} {'Count':>8} {'P25':>8} {'Median':>8} {'P75':>8} {'Mean':>8}")
    print("-" * 140)

    for idx, row in ticker_stats_df.iterrows():
        print(f"{row['ticker']:<30} {row['category']:<30} {row['count']:>8} "
              f"{row['p25_gap']:>7.0f}m {row['median_gap']:>7.0f}m {row['p75_gap']:>7.0f}m {row['mean_gap']:>7.0f}m")

    print()

    # Save detailed breakdown
    ticker_stats_df.to_csv('stability_waiting_period_by_ticker.csv', index=False)

    # Accuracy by waiting period
    print("=" * 100)
    print("ACCURACY vs WAITING PERIOD")
    print("If bot waits X minutes after first touch, what accuracy?")
    print("=" * 100)
    print()

    # For this, we need to check: for each waiting period, how many markets would we correctly bet on?
    waiting_periods = [1, 5, 10, 15, 30, 60, 120, 180]

    print(f"{'Wait Time':<12} {'Markets Captured':>18} {'% of Total':>12} {'Accuracy':>10} {'Profitable?':>12}")
    print("-" * 100)

    for wait_min in waiting_periods:
        # Markets where we would bet (time_gap <= wait_min OR immediate stable)
        would_bet = price_df[
            (price_df['Time_Gap_Min'] <= wait_min)
        ]

        if len(would_bet) > 0:
            wins = (would_bet['Prediction Correct'] == 'CORRECT').sum()
            accuracy = (wins / len(would_bet)) * 100
            status = 'YES' if accuracy > 91 else 'NO'
            pct_captured = len(would_bet) / len(price_df) * 100

            print(f"{wait_min:>3} min      {len(would_bet):>10,} ({pct_captured:>5.1f}%) {pct_captured:>12.1f}% {accuracy:>9.1f}% {status:>12}")

    print()

    # Optimal waiting period
    print("=" * 100)
    print("RECOMMENDATION: Optimal Waiting Period")
    print("=" * 100)
    print()

    print("Based on the data:")
    print()

    median_gap = unstable_df['Time_Gap_Min'].median()
    p75_gap = unstable_df['Time_Gap_Min'].quantile(0.75)

    print(f"1. CONSERVATIVE (wait for median): {median_gap:.0f} minutes")
    print(f"   - Captures 50% of unstable markets")
    print(f"   - High confidence in stability")
    print()

    print(f"2. BALANCED (wait for 75th percentile): {p75_gap:.0f} minutes")
    print(f"   - Captures 75% of unstable markets")
    print(f"   - Good balance of coverage vs confidence")
    print()

    print("3. ALTERNATIVE: Use time remaining as signal")
    print("   - If time_remaining < 60min: Bet immediately (90% accurate)")
    print("   - If time_remaining > 60min: Wait for stability")
    print()

    # Correlation: time_remaining vs time_gap
    print("=" * 100)
    print("CORRELATION: Time remaining vs stability gap")
    print("=" * 100)
    print()

    unstable_df['Time_Remaining_Hours'] = (unstable_df['Close_DT'] - unstable_df['First_Touch_DT']).dt.total_seconds() / 3600

    print("Does time-to-close affect how long it takes to stabilize?")
    print()

    time_remaining_buckets = [
        ('0-1 hour', 0, 1),
        ('1-3 hours', 1, 3),
        ('3-6 hours', 3, 6),
        ('6-24 hours', 6, 24),
        ('24+ hours', 24, float('inf'))
    ]

    print(f"{'Time Remaining':<15} {'Markets':>10} {'Median Gap':>15} {'Mean Gap':>12}")
    print("-" * 100)

    for label, low, high in time_remaining_buckets:
        bucket_df = unstable_df[
            (unstable_df['Time_Remaining_Hours'] >= low) &
            (unstable_df['Time_Remaining_Hours'] < high)
        ]

        if len(bucket_df) > 0:
            median_gap = bucket_df['Time_Gap_Min'].median()
            mean_gap = bucket_df['Time_Gap_Min'].mean()
            print(f"{label:<15} {len(bucket_df):>10,} {median_gap:>12.1f} min {mean_gap:>10.1f} min")

    print()
    print("✅ Analysis complete!")
    print()

if __name__ == "__main__":
    main()
