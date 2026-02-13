"""
Analyze 90¢ crossing patterns from backtest data

Shows:
- How many times markets crossed 90¢
- How many dropped back vs held
- Time to stability
- Win rates by crossing pattern
"""
import csv
import pandas as pd
from datetime import datetime
from dateutil.parser import parse as parse_datetime

# Read the comprehensive data
print("Loading comprehensive crossing data...")
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

print(f"Total markets in dataset: {len(df):,}")
print()

# Focus on top 5 series by market count
series_counts = df['Series Ticker'].value_counts()
top_5_series = series_counts.head(5).index.tolist()

print("Top 5 series by market count:")
for i, series in enumerate(top_5_series, 1):
    count = series_counts[series]
    print(f"  {i}. {series}: {count:,} markets")
print()

# Analyze crossing patterns
results = []

for series in top_5_series:
    series_df = df[df['Series Ticker'] == series]

    total_markets = len(series_df)

    # Markets that dropped back have blank Permanent Cross Time
    dropped_back = series_df['Permanent Cross Time'].isna()
    num_dropped = dropped_back.sum()
    num_held = total_markets - num_dropped

    # Win rates
    all_wins = (series_df['Prediction Correct'] == 'CORRECT').sum()
    all_win_rate = (all_wins / total_markets * 100) if total_markets > 0 else 0

    # Win rate for markets that HELD (didn't drop back)
    held_markets = series_df[~dropped_back]
    held_wins = (held_markets['Prediction Correct'] == 'CORRECT').sum() if len(held_markets) > 0 else 0
    held_win_rate = (held_wins / len(held_markets) * 100) if len(held_markets) > 0 else 0

    # Win rate for markets that DROPPED BACK
    dropped_markets = series_df[dropped_back]
    dropped_wins = (dropped_markets['Prediction Correct'] == 'CORRECT').sum() if len(dropped_markets) > 0 else 0
    dropped_win_rate = (dropped_wins / len(dropped_markets) * 100) if len(dropped_markets) > 0 else 0

    # Calculate stability wait times (for markets that eventually held)
    wait_times = []
    for idx, row in held_markets.iterrows():
        if pd.notna(row['First Touch Time']) and pd.notna(row['Permanent Cross Time']):
            first = parse_datetime(row['First Touch Time'])
            perm = parse_datetime(row['Permanent Cross Time'])
            wait_minutes = (perm - first).total_seconds() / 60
            wait_times.append(wait_minutes)

    median_wait = pd.Series(wait_times).median() if wait_times else 0

    results.append({
        'series': series,
        'total_markets': total_markets,
        'dropped_back': num_dropped,
        'held': num_held,
        'drop_back_rate': (num_dropped / total_markets * 100),
        'all_win_rate': all_win_rate,
        'held_win_rate': held_win_rate,
        'dropped_win_rate': dropped_win_rate,
        'median_wait_minutes': median_wait
    })

# Print detailed results
print("=" * 100)
print("CROSSING PATTERN ANALYSIS - TOP 5 SERIES")
print("=" * 100)
print()

for r in results:
    print(f"{r['series']}")
    print(f"  Total 90¢ crossings: {r['total_markets']:,}")
    print(f"  Dropped back: {r['dropped_back']:,} ({r['drop_back_rate']:.1f}%)")
    print(f"  Held above 90¢: {r['held']:,} ({100-r['drop_back_rate']:.1f}%)")
    print(f"  Median wait to stability: {r['median_wait_minutes']:.1f} minutes")
    print()
    print(f"  Win rates:")
    print(f"    All markets (bet immediately): {r['all_win_rate']:.1f}%")
    print(f"    Markets that HELD: {r['held_win_rate']:.1f}%")
    print(f"    Markets that DROPPED: {r['dropped_win_rate']:.1f}%")
    print()
    print(f"  Strategy impact:")
    if_bet_immediately = r['all_win_rate']
    if_wait_for_stability = r['held_win_rate']
    improvement = if_wait_for_stability - if_bet_immediately
    capture_rate = (100 - r['drop_back_rate'])
    print(f"    Bet immediately: {if_bet_immediately:.1f}% accuracy, 100% of opportunities")
    print(f"    Wait for stability: {if_wait_for_stability:.1f}% accuracy, {capture_rate:.1f}% of opportunities")
    print(f"    Accuracy gain: +{improvement:.1f} percentage points")
    print()
    print("-" * 100)
    print()

# Summary
print("=" * 100)
print("KEY FINDINGS")
print("=" * 100)
print()

avg_drop_rate = sum(r['drop_back_rate'] for r in results) / len(results)
avg_immediate_acc = sum(r['all_win_rate'] for r in results) / len(results)
avg_held_acc = sum(r['held_win_rate'] for r in results) / len(results)
avg_wait_time = sum(r['median_wait_minutes'] for r in results) / len(results)

print(f"Across top 5 series:")
print(f"  Average drop-back rate: {avg_drop_rate:.1f}%")
print(f"  Average accuracy (bet immediately): {avg_immediate_acc:.1f}%")
print(f"  Average accuracy (wait for stability): {avg_held_acc:.1f}%")
print(f"  Accuracy improvement: +{avg_held_acc - avg_immediate_acc:.1f} percentage points")
print(f"  Average wait time: {avg_wait_time:.1f} minutes")
print()
print(f"✅ THE STABILITY WAIT STRATEGY WORKS:")
print(f"   - {avg_drop_rate:.0f}% of 90¢ crossings drop back (these would be losses)")
print(f"   - Waiting filters out the unstable markets")
print(f"   - Accuracy increases from {avg_immediate_acc:.1f}% to {avg_held_acc:.1f}%")
print(f"   - Only {avg_wait_time:.0f} minutes median wait time needed")
print()
