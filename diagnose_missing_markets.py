"""
Diagnose which series tickers lost the most markets in timing analysis.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory

def get_first_touch_pct_bucket(pct):
    """Bucket by % of market life elapsed when it first touched 90¢."""
    if pd.isna(pct):
        return 'MISSING_DATA'
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

print("=" * 100)
print("DIAGNOSTIC: Which series tickers lost markets in timing analysis?")
print("=" * 100)
print()

# Load data
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
api_df = pd.read_csv('market_open_close_times_for_analysis.csv')

print(f"Starting markets: {len(df):,}")
print(f"API markets: {len(api_df):,}")
print()

# Parse timestamps
df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
api_df['API_Open_DT'] = pd.to_datetime(api_df['open_time'], format='ISO8601')
api_df['API_Close_DT'] = pd.to_datetime(api_df['close_time'], format='ISO8601')

# Merge
merged = df.merge(
    api_df[['ticker', 'API_Open_DT', 'API_Close_DT']],
    left_on='Ticker',
    right_on='ticker',
    how='left'
)

# Calculate timing
merged['Market_Duration_Hours'] = (merged['API_Close_DT'] - merged['API_Open_DT']).dt.total_seconds() / 3600
merged['Time_Elapsed_At_First_Touch'] = (merged['First_Touch_DT'] - merged['API_Open_DT']).dt.total_seconds() / 3600
merged['First_Touch_Pct'] = (merged['Time_Elapsed_At_First_Touch'] / merged['Market_Duration_Hours']) * 100

# Filter for 90-92¢
price_df = merged[
    (merged['First Touch Price (¢)'] >= 90) &
    (merged['First Touch Price (¢)'] < 93)
].copy()

print(f"Markets in 90-92¢ range: {len(price_df):,}")
print()

# Add timing bucket
price_df['Timing_Bucket'] = price_df['First_Touch_Pct'].apply(get_first_touch_pct_bucket)

# Categorize by loss reason
price_df['Loss_Reason'] = price_df.apply(
    lambda row: 'NO_API_DATA' if pd.isna(row['API_Open_DT'])
    else 'VALID' if row['Timing_Bucket'] in ['0-25%', '25-50%', '50-75%', '75-100%']
    else row['Timing_Bucket'],
    axis=1
)

# Count by series ticker and loss reason
loss_summary = price_df.groupby(['Series Ticker', 'Loss_Reason']).size().reset_index(name='count')
loss_pivot = loss_summary.pivot(index='Series Ticker', columns='Loss_Reason', values='count').fillna(0)

# Add total column
if 'VALID' not in loss_pivot.columns:
    loss_pivot['VALID'] = 0
if 'NO_API_DATA' not in loss_pivot.columns:
    loss_pivot['NO_API_DATA'] = 0
if 'NEGATIVE' not in loss_pivot.columns:
    loss_pivot['NEGATIVE'] = 0
if 'OVER_100' not in loss_pivot.columns:
    loss_pivot['OVER_100'] = 0
if 'MISSING_DATA' not in loss_pivot.columns:
    loss_pivot['MISSING_DATA'] = 0

loss_pivot['Total_Markets'] = loss_pivot.sum(axis=1)
loss_pivot['Lost_Markets'] = loss_pivot['Total_Markets'] - loss_pivot['VALID']
loss_pivot['Loss_Pct'] = (loss_pivot['Lost_Markets'] / loss_pivot['Total_Markets'] * 100).round(1)

# Sort by lost markets
loss_pivot = loss_pivot.sort_values('Lost_Markets', ascending=False)

# Show top losers
print("=" * 120)
print("TOP 30 SERIES TICKERS BY LOST MARKETS")
print("=" * 120)
print()
print(f"{'Series Ticker':<40} {'Total':>8} {'Valid':>8} {'Lost':>8} {'Loss %':>8} {'No API':>8} {'Negative':>8} {'Over 100':>8} {'Missing':>8}")
print("-" * 120)

for ticker, row in loss_pivot.head(30).iterrows():
    print(f"{ticker:<40} {int(row['Total_Markets']):>8} {int(row['VALID']):>8} {int(row['Lost_Markets']):>8} "
          f"{row['Loss_Pct']:>7.1f}% {int(row['NO_API_DATA']):>8} {int(row['NEGATIVE']):>8} "
          f"{int(row['OVER_100']):>8} {int(row['MISSING_DATA']):>8}")

print()
print("=" * 120)
print("OVERALL SUMMARY")
print("=" * 120)
print()

total_markets = len(price_df)
valid_markets = (price_df['Loss_Reason'] == 'VALID').sum()
no_api = (price_df['Loss_Reason'] == 'NO_API_DATA').sum()
negative = (price_df['Loss_Reason'] == 'NEGATIVE').sum()
over_100 = (price_df['Loss_Reason'] == 'OVER_100').sum()
missing = (price_df['Loss_Reason'] == 'MISSING_DATA').sum()

print(f"Total markets (90-92¢): {total_markets:,}")
print(f"  Valid timing (0-100%): {valid_markets:,} ({valid_markets/total_markets*100:.1f}%)")
print(f"  No API data: {no_api:,} ({no_api/total_markets*100:.1f}%)")
print(f"  Negative timing: {negative:,} ({negative/total_markets*100:.1f}%)")
print(f"  Over 100% timing: {over_100:,} ({over_100/total_markets*100:.1f}%)")
print(f"  Missing data: {missing:,} ({missing/total_markets*100:.1f}%)")
print()

# Save detailed breakdown
loss_pivot.to_csv('market_loss_by_series_ticker.csv')
print(f"✅ Saved detailed breakdown to market_loss_by_series_ticker.csv")
print()
