"""
Analyze ALL KXATPMATCH and KXWTAMATCH markets across entire backtest history.
Show monthly accuracy trends to see if recent success is consistent or just a lucky week.
"""

import pandas as pd
from datetime import datetime

# Load data
print("Loading backtest data...")
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

# Parse timestamps
df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')
df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

# Filter for tennis markets (any price, any timing - we want ALL tennis data)
tennis_df = df[df['Series Ticker'].isin(['KXATPMATCH', 'KXWTAMATCH'])].copy()

print("=" * 100)
print(f"FOUND {len(tennis_df):,} TOTAL TENNIS MARKETS IN BACKTEST CSV")
print("=" * 100)
print()

if len(tennis_df) == 0:
    print("❌ NO TENNIS DATA FOUND")
    exit(0)

# Calculate profit
tennis_df['Profit'] = tennis_df.apply(
    lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
               else -row['First Touch Price (¢)'],
    axis=1
)

# Add month column
tennis_df['Month'] = tennis_df['Close_DT'].dt.to_period('M')

# Overall stats
print("OVERALL TENNIS STATS (ALL MARKETS, ALL PRICES, ALL TIMING)")
print("-" * 100)
total = len(tennis_df)
wins = (tennis_df['Prediction Correct'] == 'CORRECT').sum()
accuracy = (wins / total) * 100
avg_profit = tennis_df['Profit'].mean()

print(f"Total markets: {total:,}")
print(f"Wins: {wins:,} | Losses: {total - wins:,}")
print(f"Accuracy: {accuracy:.1f}%")
print(f"Avg Profit: {avg_profit:+.2f}¢")
print(f"Date Range: {tennis_df['Close_DT'].min().strftime('%Y-%m-%d')} to {tennis_df['Close_DT'].max().strftime('%Y-%m-%d')}")
print()

# Breakdown by series
print("=" * 100)
print("BREAKDOWN BY SERIES")
print("=" * 100)
print()

for series in ['KXATPMATCH', 'KXWTAMATCH']:
    series_df = tennis_df[tennis_df['Series Ticker'] == series]

    if len(series_df) == 0:
        print(f"{series}: No data")
        print()
        continue

    total_s = len(series_df)
    wins_s = (series_df['Prediction Correct'] == 'CORRECT').sum()
    accuracy_s = (wins_s / total_s) * 100
    avg_profit_s = series_df['Profit'].mean()

    print(f"{series}")
    print(f"  Total: {total_s:,} | Wins: {wins_s:,} | Losses: {total_s - wins_s:,}")
    print(f"  Accuracy: {accuracy_s:.1f}% | Avg Profit: {avg_profit_s:+.2f}¢")
    print(f"  Date Range: {series_df['Close_DT'].min().strftime('%Y-%m-%d')} to {series_df['Close_DT'].max().strftime('%Y-%m-%d')}")
    print()

# Monthly breakdown
print("=" * 100)
print("MONTHLY ACCURACY TRENDS (ALL TENNIS MARKETS)")
print("=" * 100)
print()

monthly_stats = tennis_df.groupby('Month').agg({
    'Ticker': 'count',
    'Prediction Correct': lambda x: (x == 'CORRECT').sum(),
    'Profit': 'mean'
}).rename(columns={'Ticker': 'Total', 'Prediction Correct': 'Wins'})

monthly_stats['Losses'] = monthly_stats['Total'] - monthly_stats['Wins']
monthly_stats['Accuracy'] = (monthly_stats['Wins'] / monthly_stats['Total']) * 100
monthly_stats['Avg_Profit'] = monthly_stats['Profit']

print(f"{'Month':<12} {'Total':>8} {'Wins':>8} {'Losses':>8} {'Accuracy':>10} {'Avg Profit':>12}")
print("-" * 100)

for month, row in monthly_stats.iterrows():
    print(f"{str(month):<12} {int(row['Total']):>8} {int(row['Wins']):>8} {int(row['Losses']):>8} "
          f"{row['Accuracy']:>9.1f}% {row['Avg_Profit']:>11.2f}¢")

print()

# Breakdown by series and month
print("=" * 100)
print("MONTHLY BREAKDOWN BY SERIES")
print("=" * 100)
print()

for series in ['KXATPMATCH', 'KXWTAMATCH']:
    series_df = tennis_df[tennis_df['Series Ticker'] == series]

    if len(series_df) == 0:
        continue

    print(f"{series}")
    print("-" * 100)

    monthly_series = series_df.groupby('Month').agg({
        'Ticker': 'count',
        'Prediction Correct': lambda x: (x == 'CORRECT').sum(),
        'Profit': 'mean'
    }).rename(columns={'Ticker': 'Total', 'Prediction Correct': 'Wins'})

    monthly_series['Losses'] = monthly_series['Total'] - monthly_series['Wins']
    monthly_series['Accuracy'] = (monthly_series['Wins'] / monthly_series['Total']) * 100
    monthly_series['Avg_Profit'] = monthly_series['Profit']

    print(f"{'Month':<12} {'Total':>8} {'Wins':>8} {'Losses':>8} {'Accuracy':>10} {'Avg Profit':>12}")
    print("-" * 100)

    for month, row in monthly_series.iterrows():
        print(f"{str(month):<12} {int(row['Total']):>8} {int(row['Wins']):>8} {int(row['Losses']):>8} "
              f"{row['Accuracy']:>9.1f}% {row['Avg_Profit']:>11.2f}¢")

    print()

# Now check the 90-92¢ / 0-1h bucket specifically by month
print("=" * 100)
print("MONTHLY BREAKDOWN: 90-92¢ PRICE + 0-1H TO CLOSE (PROFITABLE BUCKET)")
print("=" * 100)
print()

profitable_df = tennis_df[
    (tennis_df['Time_To_Close_Hours'] >= 0) &
    (tennis_df['Time_To_Close_Hours'] < 1) &
    (tennis_df['First Touch Price (¢)'] >= 90) &
    (tennis_df['First Touch Price (¢)'] < 93)
].copy()

if len(profitable_df) == 0:
    print("❌ No markets in the 90-92¢ / 0-1h bucket")
else:
    print(f"Total markets in profitable bucket: {len(profitable_df):,}")
    print(f"Date range: {profitable_df['Close_DT'].min().strftime('%Y-%m-%d')} to {profitable_df['Close_DT'].max().strftime('%Y-%m-%d')}")
    print()

    monthly_profitable = profitable_df.groupby('Month').agg({
        'Ticker': 'count',
        'Prediction Correct': lambda x: (x == 'CORRECT').sum(),
        'Profit': 'mean'
    }).rename(columns={'Ticker': 'Total', 'Prediction Correct': 'Wins'})

    monthly_profitable['Losses'] = monthly_profitable['Total'] - monthly_profitable['Wins']
    monthly_profitable['Accuracy'] = (monthly_profitable['Wins'] / monthly_profitable['Total']) * 100
    monthly_profitable['Avg_Profit'] = monthly_profitable['Profit']

    print(f"{'Month':<12} {'Total':>8} {'Wins':>8} {'Losses':>8} {'Accuracy':>10} {'Avg Profit':>12}")
    print("-" * 100)

    for month, row in monthly_profitable.iterrows():
        print(f"{str(month):<12} {int(row['Total']):>8} {int(row['Wins']):>8} {int(row['Losses']):>8} "
              f"{row['Accuracy']:>9.1f}% {row['Avg_Profit']:>11.2f}¢")

    print()

print("=" * 100)
print("CONCLUSION")
print("=" * 100)

months_count = len(monthly_stats)
if months_count <= 1:
    print("⚠️  WARNING: Only 1 month of data - NOT ENOUGH HISTORY TO TRUST")
    print(f"   All data is from {monthly_stats.index[0]}")
    print("   This could be a lucky week, not a persistent pattern")
elif months_count <= 3:
    print("⚠️  CAUTION: Only a few months of data")
    print(f"   Data spans {months_count} months")
    print("   Pattern may not be fully validated")
else:
    print(f"✅ Multiple months of data ({months_count} months)")
    print("   Pattern has more historical support")

print()
