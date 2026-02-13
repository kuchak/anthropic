"""
Generate series-ticker-specific wait times based on stability analysis.

Uses median stability gap data to set optimal wait times:
- 0-5 min gap → 1 min wait (fast stabilization)
- 5-15 min gap → 3 min wait (medium stabilization)
- 15-60 min gap → 5 min wait (slow stabilization)
- 60+ min gap → EXCLUDE (too unstable for real-time trading)
"""

import pandas as pd
import yaml

def main():
    print("=" * 100)
    print("GENERATING SERIES-TICKER-SPECIFIC WAIT TIMES")
    print("=" * 100)
    print()

    # Load stability data
    stability_df = pd.read_csv('stability_waiting_period_by_ticker.csv')
    print(f"Loaded stability data for {len(stability_df)} series tickers")
    print()

    # Classify tickers by median stability gap
    fast_tickers = []      # 0-5 min gap → 1 min wait
    medium_tickers = []    # 5-15 min gap → 3 min wait
    slow_tickers = []      # 15-60 min gap → 5 min wait
    exclude_tickers = []   # 60+ min gap → EXCLUDE

    ticker_wait_times = {}

    for idx, row in stability_df.iterrows():
        ticker = row['ticker']
        median_gap = row['median_gap']
        category = row['category']
        count = row['count']

        if median_gap < 5:
            fast_tickers.append((ticker, category, median_gap, count))
            ticker_wait_times[ticker] = {
                'wait_minutes': 1,
                'median_gap_minutes': median_gap,
                'category': category,
                'sample_size': count
            }
        elif median_gap < 15:
            medium_tickers.append((ticker, category, median_gap, count))
            ticker_wait_times[ticker] = {
                'wait_minutes': 3,
                'median_gap_minutes': median_gap,
                'category': category,
                'sample_size': count
            }
        elif median_gap < 60:
            slow_tickers.append((ticker, category, median_gap, count))
            ticker_wait_times[ticker] = {
                'wait_minutes': 5,
                'median_gap_minutes': median_gap,
                'category': category,
                'sample_size': count
            }
        else:
            exclude_tickers.append((ticker, category, median_gap, count))
            # Don't add to ticker_wait_times - these are excluded

    print("=" * 100)
    print("CLASSIFICATION RESULTS")
    print("=" * 100)
    print()

    print(f"FAST (1-minute wait, median gap < 5 min):     {len(fast_tickers)} tickers")
    print(f"MEDIUM (3-minute wait, median gap 5-15 min):  {len(medium_tickers)} tickers")
    print(f"SLOW (5-minute wait, median gap 15-60 min):   {len(slow_tickers)} tickers")
    print(f"EXCLUDED (median gap 60+ min):                {len(exclude_tickers)} tickers")
    print()

    # Display each category
    print("=" * 100)
    print("FAST STABILIZATION (1-minute wait)")
    print("=" * 100)
    print(f"{'Series Ticker':<30} {'Category':<30} {'Median Gap':>12} {'Sample Size':>12}")
    print("-" * 100)
    for ticker, category, gap, count in sorted(fast_tickers, key=lambda x: x[2]):
        print(f"{ticker:<30} {category:<30} {gap:>10.1f}m {count:>12}")
    print()

    print("=" * 100)
    print("MEDIUM STABILIZATION (3-minute wait)")
    print("=" * 100)
    print(f"{'Series Ticker':<30} {'Category':<30} {'Median Gap':>12} {'Sample Size':>12}")
    print("-" * 100)
    for ticker, category, gap, count in sorted(medium_tickers, key=lambda x: x[2]):
        print(f"{ticker:<30} {category:<30} {gap:>10.1f}m {count:>12}")
    print()

    print("=" * 100)
    print("SLOW STABILIZATION (5-minute wait)")
    print("=" * 100)
    print(f"{'Series Ticker':<30} {'Category':<30} {'Median Gap':>12} {'Sample Size':>12}")
    print("-" * 100)
    for ticker, category, gap, count in sorted(slow_tickers, key=lambda x: x[2]):
        print(f"{ticker:<30} {category:<30} {gap:>10.1f}m {count:>12}")
    print()

    print("=" * 100)
    print("EXCLUDED TICKERS (too unstable for real-time trading)")
    print("=" * 100)
    print(f"{'Series Ticker':<30} {'Category':<30} {'Median Gap':>12} {'Sample Size':>12}")
    print("-" * 100)
    for ticker, category, gap, count in sorted(exclude_tickers, key=lambda x: x[2]):
        gap_hours = gap / 60
        if gap_hours < 24:
            gap_str = f"{gap_hours:.1f}h"
        else:
            gap_days = gap_hours / 24
            gap_str = f"{gap_days:.1f}d"
        print(f"{ticker:<30} {category:<30} {gap_str:>12} {count:>12}")
    print()

    # Save ticker wait times configuration
    config = {
        'series_ticker_wait_times': ticker_wait_times,
        'metadata': {
            'fast_count': len(fast_tickers),
            'medium_count': len(medium_tickers),
            'slow_count': len(slow_tickers),
            'excluded_count': len(exclude_tickers),
            'total_analyzed': len(stability_df),
            'classification': {
                'fast': '< 5 min median gap → 1 min wait',
                'medium': '5-15 min median gap → 3 min wait',
                'slow': '15-60 min median gap → 5 min wait',
                'excluded': '60+ min median gap → do not trade'
            }
        }
    }

    # Save to YAML
    with open('ticker_wait_times_config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("=" * 100)
    print("CONFIGURATION GENERATED")
    print("=" * 100)
    print()
    print("✅ Saved to: ticker_wait_times_config.yaml")
    print()
    print(f"Total tickers with wait times: {len(ticker_wait_times)}")
    print(f"  Fast (1 min): {len(fast_tickers)}")
    print(f"  Medium (3 min): {len(medium_tickers)}")
    print(f"  Slow (5 min): {len(slow_tickers)}")
    print()
    print(f"Excluded tickers: {len(exclude_tickers)}")
    print()

    # Generate summary table for documentation
    print("=" * 100)
    print("SUMMARY BY CATEGORY")
    print("=" * 100)
    print()

    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)

    for ticker, category, gap, count in fast_tickers:
        by_category[category].append(('FAST', ticker, gap, count))
    for ticker, category, gap, count in medium_tickers:
        by_category[category].append(('MEDIUM', ticker, gap, count))
    for ticker, category, gap, count in slow_tickers:
        by_category[category].append(('SLOW', ticker, gap, count))
    for ticker, category, gap, count in exclude_tickers:
        by_category[category].append(('EXCLUDE', ticker, gap, count))

    for category, items in sorted(by_category.items()):
        print(f"\n{category}:")
        print(f"  Fast: {sum(1 for x in items if x[0] == 'FAST')}")
        print(f"  Medium: {sum(1 for x in items if x[0] == 'MEDIUM')}")
        print(f"  Slow: {sum(1 for x in items if x[0] == 'SLOW')}")
        print(f"  Excluded: {sum(1 for x in items if x[0] == 'EXCLUDE')}")

    print()
    print("=" * 100)
    print("RECOMMENDED BOT CONFIGURATION")
    print("=" * 100)
    print()
    print("To use this configuration in the bot:")
    print()
    print("1. Add to config.yaml:")
    print("   series_ticker_wait_times: !include ticker_wait_times_config.yaml")
    print()
    print("2. Or manually copy the wait times for each ticker you want to trade")
    print()
    print("3. Bot logic:")
    print("   - When price first hits 90¢, start timer")
    print("   - Wait for ticker-specific duration (1, 3, or 5 minutes)")
    print("   - If price still >= 90¢ after wait, place bet")
    print("   - If price drops below 90¢ during wait, reset timer")
    print()

    # Generate a simplified whitelist for the fastest/most reliable markets
    print("=" * 100)
    print("RECOMMENDED WHITELIST (fast + high sample size)")
    print("=" * 100)
    print()

    # Recommend fast tickers with at least 25 samples
    recommended = [
        (ticker, category, gap, count)
        for ticker, category, gap, count in fast_tickers
        if count >= 25
    ]

    print(f"Recommended tickers: {len(recommended)}")
    print()
    print("series_ticker_whitelist:")
    for ticker, category, gap, count in sorted(recommended, key=lambda x: x[2]):
        print(f"  - {ticker:<30}  # {category:<30} (median gap: {gap:.1f}m, n={count})")

    print()
    print("✅ Analysis complete!")
    print()

if __name__ == "__main__":
    main()
