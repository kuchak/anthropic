"""
Validate ticker wait times against actual profitability.

Cross-reference:
1. Ticker wait times (from stability analysis)
2. Permanent cross accuracy (from backtest)
3. Profitability threshold: 91% accuracy minimum

Only include tickers that are BOTH:
- Fast/medium stabilizing (< 60 min gap)
- Profitable (> 91% accuracy at 90-92¢)
"""

import pandas as pd
import yaml

def main():
    print("=" * 100)
    print("VALIDATING TICKER PROFITABILITY")
    print("Cross-referencing wait times with accuracy data")
    print("=" * 100)
    print()

    # Load wait times config
    with open('ticker_wait_times_config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    wait_times = config['series_ticker_wait_times']
    print(f"Loaded wait times for {len(wait_times)} tickers")
    print()

    # Load comprehensive backtest data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
    print(f"Loaded {len(df):,} markets from backtest")
    print()

    # Filter to 90-92¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-92¢ range: {len(price_df):,}")
    print()

    # Calculate accuracy by series ticker
    ticker_stats = []

    for ticker in wait_times.keys():
        # Get markets for this ticker
        ticker_markets = price_df[price_df['Series Ticker'] == ticker]

        if len(ticker_markets) == 0:
            print(f"⚠️  WARNING: {ticker} has wait time but NO markets in 90-92¢ range!")
            continue

        # Calculate accuracy
        total = len(ticker_markets)
        wins = (ticker_markets['Prediction Correct'] == 'CORRECT').sum()
        accuracy = (wins / total) * 100 if total > 0 else 0

        # Get wait time info
        wait_info = wait_times[ticker]
        wait_minutes = wait_info['wait_minutes']
        median_gap = wait_info['median_gap_minutes']
        category = wait_info['category']

        # Determine if profitable (> 91% accuracy threshold)
        profitable = accuracy > 91.0

        ticker_stats.append({
            'ticker': ticker,
            'category': category,
            'wait_minutes': wait_minutes,
            'median_gap_minutes': median_gap,
            'total_markets': total,
            'wins': wins,
            'accuracy': accuracy,
            'profitable': profitable
        })

    # Convert to DataFrame
    stats_df = pd.DataFrame(ticker_stats)

    # Sort by wait time, then accuracy
    stats_df = stats_df.sort_values(['wait_minutes', 'accuracy'], ascending=[True, False])

    print("=" * 140)
    print("COMPLETE TICKER ANALYSIS (90-92¢ range)")
    print("=" * 140)
    print()

    print(f"{'Ticker':<30} {'Category':<20} {'Wait':>6} {'Gap':>8} {'Markets':>8} {'Wins':>8} {'Accuracy':>10} {'Profitable?':>12}")
    print("-" * 140)

    for idx, row in stats_df.iterrows():
        status = "✅ YES" if row['profitable'] else "❌ NO"
        print(f"{row['ticker']:<30} {row['category']:<20} {row['wait_minutes']:>4}m {row['median_gap_minutes']:>7.1f}m "
              f"{row['total_markets']:>8} {row['wins']:>8} {row['accuracy']:>9.1f}% {status:>12}")

    print()

    # Summary by wait time category
    print("=" * 100)
    print("SUMMARY BY WAIT TIME CATEGORY")
    print("=" * 100)
    print()

    for wait_time in [1, 3, 5]:
        wait_df = stats_df[stats_df['wait_minutes'] == wait_time]
        profitable_df = wait_df[wait_df['profitable']]

        if len(wait_df) > 0:
            print(f"{wait_time}-MINUTE WAIT:")
            print(f"  Total tickers: {len(wait_df)}")
            print(f"  Profitable (>91%): {len(profitable_df)} ({len(profitable_df)/len(wait_df)*100:.1f}%)")
            print(f"  NOT profitable (≤91%): {len(wait_df) - len(profitable_df)}")
            print(f"  Avg accuracy: {wait_df['accuracy'].mean():.1f}%")
            if len(profitable_df) > 0:
                print(f"  Avg accuracy (profitable only): {profitable_df['accuracy'].mean():.1f}%")
            print()

    # Filter to profitable only
    profitable_df = stats_df[stats_df['profitable']].copy()

    print("=" * 140)
    print("FILTERED: PROFITABLE TICKERS ONLY (accuracy > 91%)")
    print("=" * 140)
    print()

    print(f"Total profitable tickers: {len(profitable_df)} out of {len(stats_df)} ({len(profitable_df)/len(stats_df)*100:.1f}%)")
    print()

    print(f"{'Ticker':<30} {'Category':<20} {'Wait':>6} {'Gap':>8} {'Markets':>8} {'Accuracy':>10}")
    print("-" * 140)

    for idx, row in profitable_df.iterrows():
        print(f"{row['ticker']:<30} {row['category']:<20} {row['wait_minutes']:>4}m {row['median_gap_minutes']:>7.1f}m "
              f"{row['total_markets']:>8} {row['accuracy']:>9.1f}%")

    print()

    # Breakdown by wait time
    print("=" * 100)
    print("PROFITABLE TICKERS BY WAIT TIME")
    print("=" * 100)
    print()

    for wait_time in [1, 3, 5]:
        wait_profitable = profitable_df[profitable_df['wait_minutes'] == wait_time]

        print(f"{wait_time}-MINUTE WAIT: {len(wait_profitable)} tickers")
        print()

        for idx, row in wait_profitable.iterrows():
            print(f"  - {row['ticker']:<30} {row['category']:<20} ({row['total_markets']:>3} markets, {row['accuracy']:.1f}% accurate)")

        print()

    # Generate recommended whitelist
    print("=" * 100)
    print("RECOMMENDED WHITELIST (profitable tickers only)")
    print("=" * 100)
    print()

    print("# config.yaml")
    print("series_ticker_whitelist:")
    for idx, row in profitable_df.iterrows():
        print(f"  - {row['ticker']:<30}  # {row['category']:<20} ({row['wait_minutes']}m wait, {row['accuracy']:.1f}% accurate, n={row['total_markets']})")

    print()

    # Save profitable tickers
    profitable_df.to_csv('profitable_tickers_with_wait_times.csv', index=False)
    print(f"✅ Saved to: profitable_tickers_with_wait_times.csv")
    print()

    # Generate wait times config for profitable tickers only
    profitable_wait_times = {}
    for idx, row in profitable_df.iterrows():
        profitable_wait_times[row['ticker']] = {
            'wait_minutes': int(row['wait_minutes']),
            'median_gap_minutes': float(row['median_gap_minutes']),
            'category': row['category'],
            'sample_size': int(row['total_markets']),
            'accuracy': float(row['accuracy'])
        }

    profitable_config = {
        'series_ticker_wait_times': profitable_wait_times,
        'metadata': {
            'total_tickers': len(profitable_df),
            'accuracy_threshold': 91.0,
            'description': 'Only includes tickers with >91% accuracy at 90-92¢ entry'
        }
    }

    with open('profitable_ticker_wait_times.yaml', 'w') as f:
        yaml.dump(profitable_config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Saved to: profitable_ticker_wait_times.yaml")
    print()

    # Analysis of rejected tickers
    rejected_df = stats_df[~stats_df['profitable']].copy()

    if len(rejected_df) > 0:
        print("=" * 140)
        print("REJECTED TICKERS (accuracy ≤ 91%)")
        print("=" * 140)
        print()

        print(f"Total rejected: {len(rejected_df)} tickers")
        print()

        print(f"{'Ticker':<30} {'Category':<20} {'Wait':>6} {'Markets':>8} {'Accuracy':>10} {'Reason':>20}")
        print("-" * 140)

        for idx, row in rejected_df.iterrows():
            reason = f"Low accuracy ({row['accuracy']:.1f}%)"
            print(f"{row['ticker']:<30} {row['category']:<20} {row['wait_minutes']:>4}m "
                  f"{row['total_markets']:>8} {row['accuracy']:>9.1f}% {reason:>20}")

        print()

    # Key insights
    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print()

    fast_profitable = profitable_df[profitable_df['wait_minutes'] == 1]
    medium_profitable = profitable_df[profitable_df['wait_minutes'] == 3]
    slow_profitable = profitable_df[profitable_df['wait_minutes'] == 5]

    print(f"1. FAST markets (1-min wait):")
    print(f"   - {len(fast_profitable)} profitable tickers")
    if len(fast_profitable) > 0:
        print(f"   - Avg accuracy: {fast_profitable['accuracy'].mean():.1f}%")
        print(f"   - Total markets: {fast_profitable['total_markets'].sum():,}")
    print()

    print(f"2. MEDIUM markets (3-min wait):")
    print(f"   - {len(medium_profitable)} profitable tickers")
    if len(medium_profitable) > 0:
        print(f"   - Avg accuracy: {medium_profitable['accuracy'].mean():.1f}%")
        print(f"   - Total markets: {medium_profitable['total_markets'].sum():,}")
    print()

    print(f"3. SLOW markets (5-min wait):")
    print(f"   - {len(slow_profitable)} profitable tickers")
    if len(slow_profitable) > 0:
        print(f"   - Avg accuracy: {slow_profitable['accuracy'].mean():.1f}%")
        print(f"   - Total markets: {slow_profitable['total_markets'].sum():,}")
    print()

    total_markets = profitable_df['total_markets'].sum()
    total_wins = profitable_df['wins'].sum()
    overall_accuracy = (total_wins / total_markets * 100) if total_markets > 0 else 0

    print(f"OVERALL (profitable tickers only):")
    print(f"  - {len(profitable_df)} tickers")
    print(f"  - {total_markets:,} total markets")
    print(f"  - {total_wins:,} wins")
    print(f"  - {overall_accuracy:.2f}% overall accuracy")
    print()

    print("=" * 100)
    print("✅ Analysis complete!")
    print("=" * 100)
    print()

if __name__ == "__main__":
    main()
