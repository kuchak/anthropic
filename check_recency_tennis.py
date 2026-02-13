"""Quick recency check: Do tennis patterns hold in recent data (Jan 2025+)?"""

import pandas as pd
from datetime import datetime

# Load data
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

# Parse timestamps
df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')
df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

# Filter for ATP and WTA
tennis_df = df[df['Series Ticker'].isin(['KXATPMATCH', 'KXWTAMATCH'])].copy()

# Filter for 0-1h to close, 90-92¢
profitable_df = tennis_df[
    (tennis_df['Time_To_Close_Hours'] >= 0) &
    (tennis_df['Time_To_Close_Hours'] < 1) &
    (tennis_df['First Touch Price (¢)'] >= 90) &
    (tennis_df['First Touch Price (¢)'] < 93)
].copy()

# Calculate profit
profitable_df['Profit'] = profitable_df.apply(
    lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
               else -row['First Touch Price (¢)'],
    axis=1
)

# Split by recency
jan2025_cutoff = pd.to_datetime('2025-01-01', utc=True)
recent_df = profitable_df[profitable_df['Close_DT'] >= jan2025_cutoff]
older_df = profitable_df[profitable_df['Close_DT'] < jan2025_cutoff]

print("=" * 100)
print("RECENCY ANALYSIS: ATP/WTA Tennis (0-1h to close, 90-92¢)")
print("=" * 100)
print()

# Overall stats
print("OVERALL (All Time)")
print("-" * 100)
total = len(profitable_df)
wins = (profitable_df['Prediction Correct'] == 'CORRECT').sum()
accuracy = (wins / total) * 100 if total > 0 else 0
avg_profit = profitable_df['Profit'].mean()
print(f"Total markets: {total}")
print(f"Wins: {wins} | Losses: {total - wins}")
print(f"Accuracy: {accuracy:.1f}%")
print(f"Avg Profit: {avg_profit:+.2f}¢")
print()

# Recent stats (Jan 2025+)
print("RECENT (Jan 2025 onwards)")
print("-" * 100)
total_recent = len(recent_df)
wins_recent = (recent_df['Prediction Correct'] == 'CORRECT').sum()
accuracy_recent = (wins_recent / total_recent) * 100 if total_recent > 0 else 0
avg_profit_recent = recent_df['Profit'].mean()
print(f"Total markets: {total_recent}")
print(f"Wins: {wins_recent} | Losses: {total_recent - wins_recent}")
print(f"Accuracy: {accuracy_recent:.1f}%")
print(f"Avg Profit: {avg_profit_recent:+.2f}¢")
print()

# Older stats (before Jan 2025)
print("OLDER (Before Jan 2025)")
print("-" * 100)
total_older = len(older_df)
wins_older = (older_df['Prediction Correct'] == 'CORRECT').sum()
accuracy_older = (wins_older / total_older) * 100 if total_older > 0 else 0
avg_profit_older = older_df['Profit'].mean()
print(f"Total markets: {total_older}")
print(f"Wins: {wins_older} | Losses: {total_older - wins_older}")
print(f"Accuracy: {accuracy_older:.1f}%")
print(f"Avg Profit: {avg_profit_older:+.2f}¢")
print()

# Breakdown by series
print("=" * 100)
print("BREAKDOWN BY SERIES (RECENT DATA ONLY - Jan 2025+)")
print("=" * 100)
print()

for series in ['KXATPMATCH', 'KXWTAMATCH']:
    series_df = recent_df[recent_df['Series Ticker'] == series]

    if len(series_df) == 0:
        print(f"{series}: No recent data")
        print()
        continue

    total_s = len(series_df)
    wins_s = (series_df['Prediction Correct'] == 'CORRECT').sum()
    accuracy_s = (wins_s / total_s) * 100
    avg_profit_s = series_df['Profit'].mean()

    print(f"{series}")
    print(f"  Markets: {total_s} | Wins: {wins_s} | Losses: {total_s - wins_s}")
    print(f"  Accuracy: {accuracy_s:.1f}% | Avg Profit: {avg_profit_s:+.2f}¢")

    # Show date range
    min_date = series_df['Close_DT'].min()
    max_date = series_df['Close_DT'].max()
    print(f"  Date Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    print()

print("=" * 100)
print("CONCLUSION")
print("=" * 100)
if total_recent > 0:
    if accuracy_recent >= accuracy_older - 5:
        print("✅ Pattern HOLDS in recent data (Jan 2025+)")
        print(f"   Recent accuracy ({accuracy_recent:.1f}%) is comparable to older data ({accuracy_older:.1f}%)")
    else:
        print("⚠️  Pattern may be DEGRADING")
        print(f"   Recent accuracy ({accuracy_recent:.1f}%) is lower than older data ({accuracy_older:.1f}%)")
else:
    print("❌ NO RECENT DATA (Jan 2025+)")
    print("   All profitable tennis markets are from before Jan 2025")
print()
