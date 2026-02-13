"""
Create detailed crossing CSV with one row per crossing event

For markets that drop back, this creates multiple rows:
- Row 1: Initial crossing (dropped_back=True)
- Row 2: Permanent crossing (dropped_back=False)
"""
import csv
import pandas as pd
from datetime import datetime
from dateutil.parser import parse as parse_datetime

# Read data
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

# Get top 5 series
series_counts = df['Series Ticker'].value_counts()
top_5_series = series_counts.head(5).index.tolist()

print(f"Creating detailed crossing CSV for top 5 series...")
print(f"Series: {', '.join(top_5_series)}")
print()

# Filter to top 5
df = df[df['Series Ticker'].isin(top_5_series)]

crossing_records = []

for idx, row in df.iterrows():
    series_ticker = row['Series Ticker']
    market_ticker = row['Ticker']
    title = row['Title']
    result = row['Result']
    settlement_cents = row['Settlement (¢)']
    close_time = row['Market Close Time']
    first_touch_time = row['First Touch Time']
    first_touch_price = row['First Touch Price (¢)']
    perm_cross_time = row['Permanent Cross Time']
    perm_cross_price = row['Permanent Cross Price (¢)']

    # Determine if market dropped back
    dropped_back = pd.isna(perm_cross_time) or (first_touch_time != perm_cross_time)

    if not dropped_back:
        # Market crossed 90¢ once and held - single crossing event
        crossing_records.append({
            'series_ticker': series_ticker,
            'market_ticker': market_ticker,
            'market_title': title,
            'crossing_number': 1,
            'cross_timestamp': first_touch_time,
            'cross_price_cents': int(first_touch_price) if pd.notna(first_touch_price) else None,
            'dropped_back': False,
            'drop_timestamp': None,
            'held_minutes': None,
            'close_time': close_time,
            'result': result,
            'settlement_cents': int(settlement_cents) if pd.notna(settlement_cents) else None,
            'would_win_if_bet': (settlement_cents == 100),  # Betting YES at 90¢+
        })

    else:
        # Market dropped back - create 2 crossing records

        # First crossing (dropped back)
        crossing_records.append({
            'series_ticker': series_ticker,
            'market_ticker': market_ticker,
            'market_title': title,
            'crossing_number': 1,
            'cross_timestamp': first_touch_time,
            'cross_price_cents': int(first_touch_price) if pd.notna(first_touch_price) else None,
            'dropped_back': True,
            'drop_timestamp': perm_cross_time if pd.notna(perm_cross_time) else close_time,  # Approximation
            'held_minutes': None,  # Unknown when it dropped
            'close_time': close_time,
            'result': result,
            'settlement_cents': int(settlement_cents) if pd.notna(settlement_cents) else None,
            'would_win_if_bet': (settlement_cents == 100),  # Betting YES at 90¢+
        })

        # If there's a permanent cross time, it crossed again and held
        if pd.notna(perm_cross_time):
            # Calculate wait time
            first = parse_datetime(first_touch_time)
            perm = parse_datetime(perm_cross_time)
            wait_minutes = (perm - first).total_seconds() / 60

            crossing_records.append({
                'series_ticker': series_ticker,
                'market_ticker': market_ticker,
                'market_title': title,
                'crossing_number': 2,
                'cross_timestamp': perm_cross_time,
                'cross_price_cents': int(perm_cross_price) if pd.notna(perm_cross_price) else None,
                'dropped_back': False,
                'drop_timestamp': None,
                'held_minutes': wait_minutes,
                'close_time': close_time,
                'result': result,
                'settlement_cents': int(settlement_cents) if pd.notna(settlement_cents) else None,
                'would_win_if_bet': (settlement_cents == 100),  # Betting YES at 90¢+
            })

# Save to CSV
output_file = 'crossing_events_top5.csv'

with open(output_file, 'w', newline='') as f:
    fieldnames = [
        'series_ticker',
        'market_ticker',
        'market_title',
        'crossing_number',
        'cross_timestamp',
        'cross_price_cents',
        'dropped_back',
        'drop_timestamp',
        'held_minutes',
        'close_time',
        'result',
        'settlement_cents',
        'would_win_if_bet'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(crossing_records)

print(f"✅ Saved {len(crossing_records)} crossing events to {output_file}")
print()

# Show sample
print("Sample data (first 10 rows):")
print()
df_crossings = pd.read_csv(output_file)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)
print(df_crossings.head(10).to_string(index=False))
print()

# Summary stats
print("=" * 100)
print("SUMMARY")
print("=" * 100)
total_crossings = len(df_crossings)
first_crossings = len(df_crossings[df_crossings['crossing_number'] == 1])
second_crossings = len(df_crossings[df_crossings['crossing_number'] == 2])
dropped_back = len(df_crossings[df_crossings['dropped_back'] == True])

print(f"Total crossing events: {total_crossings:,}")
print(f"First crossings: {first_crossings:,}")
print(f"Second crossings (after drop): {second_crossings:,}")
print(f"Crossings that dropped back: {dropped_back:,} ({dropped_back/first_crossings*100:.1f}% of first crossings)")
print()

# Win rates by crossing type
first_cross_wins = df_crossings[(df_crossings['crossing_number'] == 1) & (df_crossings['would_win_if_bet'] == True)]
first_cross_total = df_crossings[df_crossings['crossing_number'] == 1]
first_cross_wr = len(first_cross_wins) / len(first_cross_total) * 100

second_cross_wins = df_crossings[(df_crossings['crossing_number'] == 2) & (df_crossings['would_win_if_bet'] == True)]
second_cross_total = df_crossings[df_crossings['crossing_number'] == 2]
second_cross_wr = len(second_cross_wins) / len(second_cross_total) * 100 if len(second_cross_total) > 0 else 0

stable_crossings = df_crossings[df_crossings['dropped_back'] == False]
stable_wins = df_crossings[(df_crossings['dropped_back'] == False) & (df_crossings['would_win_if_bet'] == True)]
stable_wr = len(stable_wins) / len(stable_crossings) * 100

print("Win rates:")
print(f"  Bet on FIRST crossing: {first_cross_wr:.1f}%")
print(f"  Bet on SECOND crossing (after drop): {second_cross_wr:.1f}%")
print(f"  Bet only on STABLE crossings (never dropped): {stable_wr:.1f}%")
print()
