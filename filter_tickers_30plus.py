"""
Filter profitable tickers to only those with 30+ markets in backtest.
Calculate Kelly fractions based on actual accuracy.
"""

import pandas as pd
import yaml
import math

def calculate_kelly_fraction(accuracy, price=0.91, max_kelly=0.25):
    """
    Calculate Kelly fraction for a given accuracy.

    Kelly% = (p * b - q) / b
    where:
    - p = win probability (accuracy)
    - q = loss probability (1 - accuracy)
    - b = odds = (1 - price) / price

    We use fractional Kelly (quarter-Kelly) to be conservative.
    """
    p = accuracy / 100
    q = 1 - p
    b = (1 - price) / price  # At 91¢: (1-0.91)/0.91 = 0.0989

    kelly = (p * b - q) / b

    # Cap at max_kelly (quarter-Kelly for safety)
    kelly = min(kelly, max_kelly)
    kelly = max(kelly, 0)  # Don't go negative

    return kelly

def main():
    print("=" * 100)
    print("FILTERING TICKERS (30+ markets only)")
    print("=" * 100)
    print()

    # Load profitable tickers
    df = pd.read_csv('profitable_tickers_with_wait_times.csv')

    print(f"Total profitable tickers: {len(df)}")
    print()

    # Filter to 30+ markets
    df_30plus = df[df['total_markets'] >= 30].copy()

    print(f"Tickers with 30+ markets: {len(df_30plus)}")
    print()

    # Sort by expected profit (descending)
    df_30plus = df_30plus.sort_values('accuracy', ascending=False)

    # Calculate Kelly fractions
    df_30plus['kelly_fraction'] = df_30plus['accuracy'].apply(
        lambda acc: calculate_kelly_fraction(acc)
    )

    print("=" * 120)
    print("FILTERED WHITELIST (30+ markets)")
    print("=" * 120)
    print()

    print(f"{'Ticker':<30} {'Category':<20} {'Wait':>6} {'Markets':>8} {'Accuracy':>10} {'Kelly %':>10}")
    print("-" * 120)

    for idx, row in df_30plus.iterrows():
        print(f"{row['ticker']:<30} {row['category']:<20} {row['wait_minutes']:>4}m "
              f"{row['total_markets']:>8} {row['accuracy']:>9.1f}% {row['kelly_fraction']*100:>9.1f}%")

    print()

    # Save filtered list
    df_30plus.to_csv('filtered_tickers_30plus.csv', index=False)

    # Generate config
    whitelist = df_30plus['ticker'].tolist()

    wait_times = {}
    kelly_fractions = {}
    ticker_accuracy = {}

    for idx, row in df_30plus.iterrows():
        ticker = row['ticker']
        wait_times[ticker] = int(row['wait_minutes'])
        kelly_fractions[ticker] = float(row['kelly_fraction'])
        ticker_accuracy[ticker] = float(row['accuracy'] / 100)

    config = {
        'series_ticker_whitelist': whitelist,
        'series_ticker_wait_times': wait_times,
        'series_ticker_kelly_fractions': kelly_fractions,
        'series_ticker_accuracy': ticker_accuracy
    }

    # Save config snippet
    with open('bot_config_snippet.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Saved to:")
    print(f"  - filtered_tickers_30plus.csv")
    print(f"  - bot_config_snippet.yaml")
    print()

    # Summary by wait time
    print("=" * 100)
    print("SUMMARY BY WAIT TIME")
    print("=" * 100)
    print()

    for wait_time in sorted(df_30plus['wait_minutes'].unique()):
        wait_df = df_30plus[df_30plus['wait_minutes'] == wait_time]
        print(f"{wait_time}-MINUTE WAIT: {len(wait_df)} tickers")
        print(f"  Avg accuracy: {wait_df['accuracy'].mean():.1f}%")
        print(f"  Avg Kelly: {wait_df['kelly_fraction'].mean()*100:.1f}%")
        for idx, row in wait_df.iterrows():
            print(f"    - {row['ticker']:<30} ({row['accuracy']:.1f}%, Kelly: {row['kelly_fraction']*100:.1f}%)")
        print()

    # Overall summary
    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)
    print()

    print(f"Total tickers: {len(df_30plus)}")
    print(f"Total markets: {df_30plus['total_markets'].sum():,}")
    print(f"Avg accuracy: {df_30plus['accuracy'].mean():.1f}%")
    print(f"Avg Kelly fraction: {df_30plus['kelly_fraction'].mean()*100:.1f}%")
    print()

    print("Kelly fraction breakdown:")
    print(f"  100% accuracy: {calculate_kelly_fraction(100)*100:.1f}% Kelly (capped at 25%)")
    print(f"  98% accuracy: {calculate_kelly_fraction(98)*100:.1f}% Kelly")
    print(f"  95% accuracy: {calculate_kelly_fraction(95)*100:.1f}% Kelly")
    print(f"  92% accuracy: {calculate_kelly_fraction(92)*100:.1f}% Kelly")
    print()

    print("✅ Ready to update bot config!")
    print()

if __name__ == "__main__":
    main()
