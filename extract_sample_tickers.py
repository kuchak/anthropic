"""Extract specific market tickers for manual verification."""

import pandas as pd

# Load the main CSV
df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

# Parse timestamps
df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
df['Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')
df['Time_To_Close_Hours'] = (df['Close_DT'] - df['First_Touch_DT']).dt.total_seconds() / 3600

# Filter for KXATPMATCH
atp_df = df[
    (df['Series Ticker'] == 'KXATPMATCH') &
    (df['Time_To_Close_Hours'] >= 0) &
    (df['Time_To_Close_Hours'] < 1) &
    (df['First Touch Price (¢)'] >= 90) &
    (df['First Touch Price (¢)'] < 93)
].copy()

# Filter for KXWTAMATCH
wta_df = df[
    (df['Series Ticker'] == 'KXWTAMATCH') &
    (df['Time_To_Close_Hours'] >= 0) &
    (df['Time_To_Close_Hours'] < 1) &
    (df['First Touch Price (¢)'] >= 90) &
    (df['First Touch Price (¢)'] < 93)
].copy()

print("=" * 100)
print("SAMPLE TICKERS FOR MANUAL VERIFICATION")
print("=" * 100)
print()

print("ATP TENNIS (KXATPMATCH) - 0-1h to close, 90-92¢ price")
print("-" * 100)
print(f"Total markets in this bucket: {len(atp_df)}")
print()

# Show 10 samples
atp_samples = atp_df.head(10)
for idx, row in atp_samples.iterrows():
    result = "✅ WIN" if row['Prediction Correct'] == 'CORRECT' else "❌ LOSS"
    profit = (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT' else -row['First Touch Price (¢)']

    print(f"{result} | {row['Ticker']}")
    print(f"     Price: {row['First Touch Price (¢)']}¢ | Time to close: {row['Time_To_Close_Hours']:.1f}h | Profit: {profit:+.2f}¢")
    print(f"     First Touch: {row['First Touch Time']}")
    print(f"     Close Time: {row['Market Close Time']}")
    print(f"     Title: {row['Title']}")
    print()

print()
print("=" * 100)
print("WTA TENNIS (KXWTAMATCH) - 0-1h to close, 90-92¢ price")
print("-" * 100)
print(f"Total markets in this bucket: {len(wta_df)}")
print()

# Show 10 samples
wta_samples = wta_df.head(10)
for idx, row in wta_samples.iterrows():
    result = "✅ WIN" if row['Prediction Correct'] == 'CORRECT' else "❌ LOSS"
    profit = (100 - row['First Touch Price (¢)']) if row['Prediction Correct'] == 'CORRECT' else -row['First Touch Price (¢)']

    print(f"{result} | {row['Ticker']}")
    print(f"     Price: {row['First Touch Price (¢)']}¢ | Time to close: {row['Time_To_Close_Hours']:.1f}h | Profit: {profit:+.2f}¢")
    print(f"     First Touch: {row['First Touch Time']}")
    print(f"     Close Time: {row['Market Close Time']}")
    print(f"     Title: {row['Title']}")
    print()

# Save to CSV for easier inspection
atp_samples[['Ticker', 'Title', 'First Touch Price (¢)', 'Time_To_Close_Hours',
             'Prediction Correct', 'First Touch Time', 'Market Close Time']].to_csv(
    'atp_samples_verification.csv', index=False
)

wta_samples[['Ticker', 'Title', 'First Touch Price (¢)', 'Time_To_Close_Hours',
             'Prediction Correct', 'First Touch Time', 'Market Close Time']].to_csv(
    'wta_samples_verification.csv', index=False
)

print()
print("=" * 100)
print("✅ Saved samples to atp_samples_verification.csv and wta_samples_verification.csv")
print("=" * 100)
