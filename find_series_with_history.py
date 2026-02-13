"""
Find which series have substantial historical data (6+ months)
so we can identify patterns we can actually trust.
"""

import pandas as pd
from datetime import datetime

# Load data
print("Loading backtest data...")
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

# Parse timestamps
df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')
df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

# Calculate profit
df['Profit'] = df.apply(
    lambda row: (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT'
               else -row['First Touch Price (¢)'],
    axis=1
)

# Analyze by series
series_stats = []

for series_ticker in df['Series Ticker'].unique():
    series_df = df[df['Series Ticker'] == series_ticker]

    total = len(series_df)
    if total < 50:  # Only look at series with 50+ markets
        continue

    wins = (series_df['Prediction Correct'] == 'CORRECT').sum()
    accuracy = (wins / total) * 100
    avg_profit = series_df['Profit'].mean()

    min_date = series_df['Close_DT'].min()
    max_date = series_df['Close_DT'].max()
    date_span_days = (max_date - min_date).days
    date_span_months = date_span_days / 30.44

    series_stats.append({
        'Series Ticker': series_ticker,
        'Category': series_df['Category'].iloc[0],
        'Total Markets': total,
        'Wins': wins,
        'Losses': total - wins,
        'Accuracy': round(accuracy, 1),
        'Avg Profit': round(avg_profit, 2),
        'First Market': min_date.strftime('%Y-%m-%d'),
        'Last Market': max_date.strftime('%Y-%m-%d'),
        'Date Span (days)': date_span_days,
        'Date Span (months)': round(date_span_months, 1)
    })

# Create dataframe
stats_df = pd.DataFrame(series_stats)

# Sort by date span (descending) - we want series with the most history
stats_df = stats_df.sort_values('Date Span (days)', ascending=False)

print("=" * 100)
print("SERIES WITH 50+ MARKETS SORTED BY HISTORICAL DEPTH")
print("=" * 100)
print()

print(f"{'Series':<25} {'Markets':>8} {'Accuracy':>10} {'Avg Profit':>12} {'Span (months)':>14} {'Date Range':<30}")
print("-" * 120)

for idx, row in stats_df.iterrows():
    print(f"{row['Series Ticker']:<25} {row['Total Markets']:>8} {row['Accuracy']:>9.1f}% "
          f"{row['Avg Profit']:>11.2f}¢ {row['Date Span (months)']:>13.1f} "
          f"{row['First Market']} to {row['Last Market']}")

# Save to CSV
stats_df.to_csv('series_historical_depth.csv', index=False)
print()
print("✅ Saved to series_historical_depth.csv")
print()

# Filter for series with 6+ months of history
historical_series = stats_df[stats_df['Date Span (months)'] >= 6]

print("=" * 100)
print(f"SERIES WITH 6+ MONTHS OF HISTORY ({len(historical_series)} series)")
print("=" * 100)
print()

if len(historical_series) > 0:
    for idx, row in historical_series.iterrows():
        print(f"{row['Series Ticker']}")
        print(f"  Category: {row['Category']}")
        print(f"  Markets: {row['Total Markets']} | Accuracy: {row['Accuracy']}% | Avg Profit: {row['Avg Profit']:+.2f}¢")
        print(f"  History: {row['Date Span (months)']:.1f} months ({row['First Market']} to {row['Last Market']})")
        print()
else:
    print("❌ NO SERIES WITH 6+ MONTHS OF HISTORY")
    print()

# Show series with less than 1 month (like tennis)
print("=" * 100)
print("⚠️  SERIES WITH <1 MONTH OF DATA (NOT TRUSTWORTHY)")
print("=" * 100)
print()

short_series = stats_df[stats_df['Date Span (months)'] < 1]
for idx, row in short_series.iterrows():
    print(f"{row['Series Ticker']}: {row['Total Markets']} markets, {row['Date Span (days)']} days, {row['Accuracy']}% accuracy")

print()
