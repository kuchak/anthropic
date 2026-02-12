"""
Extract REAL accuracy data from comprehensive backtest results
Analyzes markets that crossed 90% probability by price range
"""
import pandas as pd
import json

print("=" * 80)
print("EXTRACTING REAL BACKTEST ACCURACY DATA")
print("=" * 80)
print()

# Load comprehensive crossed 90 data
csv_file = '/home/user/anthropic/comprehensive_crossed_90_detailed.csv'

try:
    df = pd.read_csv(csv_file)
    print(f"✅ Loaded {len(df)} markets that crossed 90%+")
    print()
except Exception as e:
    print(f"❌ Error loading data: {e}")
    exit(1)

print("📋 Columns:")
print(f"   {', '.join(df.columns.tolist())}")
print()

# Check what columns we have for price and result
print("Sample data (first 3 rows):")
print(df.head(3).to_string())
print()

# Find price column
price_col = None
for col in ['Permanent Cross Price (¢)', 'First Touch Price (¢)', 'crossing_price', 'price', 'final_price', 'yes_price']:
    if col in df.columns:
        price_col = col
        break

if not price_col:
    print("❌ No price column found!")
    exit(1)

print(f"Using price column: {price_col}")
print()

# Find result column
result_col = None
for col in ['Prediction Correct', 'result', 'outcome', 'correct', 'prediction_correct']:
    if col in df.columns:
        result_col = col
        break

if not result_col:
    print("❌ No result column found!")
    exit(1)

print(f"Using result column: {result_col}")
print()

# Convert price to 0-1 range if needed
df_clean = df[df[price_col].notna()].copy()

sample_price = df_clean[price_col].iloc[0] if len(df_clean) > 0 else 0
if sample_price > 1:
    df_clean['price_normalized'] = df_clean[price_col] / 100
    print(f"✅ Converted prices from cents to dollars (sample: {sample_price} → {sample_price/100})")
else:
    df_clean['price_normalized'] = df_clean[price_col]
    print(f"✅ Prices already in dollars (sample: {sample_price})")
print()

# Determine what counts as a "win"
result_values = df_clean[result_col].value_counts()
print(f"Result values: {dict(result_values)}")

# Assume 'yes' or 'CORRECT' or True means win
wins_value = None
if 'yes' in result_values.index:
    wins_value = 'yes'
elif 'CORRECT' in result_values.index:
    wins_value = 'CORRECT'
elif True in result_values.index:
    wins_value = True
elif 1 in result_values.index:
    wins_value = 1

print(f"Win indicator: {wins_value}")
print()

# Calculate overall accuracy
total = len(df_clean)
wins = (df_clean[result_col] == wins_value).sum()
overall_acc = (wins / total * 100) if total > 0 else 0

print("=" * 80)
print("📊 OVERALL RESULTS (All markets that crossed 90%+)")
print("=" * 80)
print()
print(f"Total markets: {total}")
print(f"Wins: {wins}")
print(f"Losses: {total - wins}")
print(f"Accuracy: {overall_acc:.1f}%")
print()

# Analyze by price range
print("=" * 80)
print("📈 ACCURACY BY PRICE RANGE")
print("=" * 80)
print()

ranges = [
    (0.00, 0.50, "Below $0.50"),
    (0.50, 0.85, "$0.50-0.85"),
    (0.85, 0.90, "$0.85-0.90 (85-90¢)"),
    (0.90, 0.95, "$0.90-0.95 (90-95¢)"),
    (0.95, 0.98, "$0.95-0.98 (95-98¢)"),
    (0.98, 1.00, "Above $0.98"),
]

config_ranges = {}

for min_p, max_p, label in ranges:
    range_df = df_clean[
        (df_clean['price_normalized'] >= min_p) &
        (df_clean['price_normalized'] <= max_p)
    ]

    if len(range_df) == 0:
        continue

    range_wins = (range_df[result_col] == wins_value).sum()
    range_total = len(range_df)
    range_acc = (range_wins / range_total * 100) if range_total > 0 else 0

    print(f"{label}:")
    print(f"  Markets: {range_total}")
    print(f"  Wins: {range_wins}")
    print(f"  Losses: {range_total - range_wins}")
    print(f"  Accuracy: {range_acc:.1f}%")
    print(f"  Decimal: {range_acc / 100:.4f}")
    print()

    # Store for config
    if min_p >= 0.85 and max_p <= 1.0 and range_total >= 5:
        if 0.85 <= min_p < 0.90:
            config_ranges['0.85-0.89'] = {
                'accuracy': range_acc / 100,
                'wins': range_wins,
                'total': range_total
            }
        elif 0.90 <= min_p < 0.95:
            config_ranges['0.90-0.95'] = {
                'accuracy': range_acc / 100,
                'wins': range_wins,
                'total': range_total
            }
        elif 0.95 <= min_p < 0.98:
            config_ranges['0.95-0.98'] = {
                'accuracy': range_acc / 100,
                'wins': range_wins,
                'total': range_total
            }

# Generate config
print("=" * 80)
print("🎯 CONFIG.YAML VALUES (from REAL backtest data)")
print("=" * 80)
print()

print("# Model Accuracy (from actual backtest results)")
print("# Data from markets that crossed 90%+ probability")
print(f"default_accuracy: {overall_acc / 100:.4f}  # {overall_acc:.1f}% overall ({wins}/{total} wins)")
print()
print("accuracy_by_price_range:")

for range_name in ['0.85-0.89', '0.90-0.95', '0.95-0.98']:
    if range_name in config_ranges:
        data = config_ranges[range_name]
        print(f'  "{range_name}": {data["accuracy"]:.4f}  # {data["accuracy"]*100:.1f}% ({data["wins"]}/{data["total"]} wins)')
    else:
        print(f'  "{range_name}": {overall_acc / 100:.4f}  # Using overall accuracy (insufficient data)')

print()
print()

# Category breakdown for reference
if 'Category' in df_clean.columns:
    print("=" * 80)
    print("📂 ACCURACY BY CATEGORY (for reference - NOT used for filtering)")
    print("=" * 80)
    print()

    for category in df_clean['Category'].unique():
        cat_df = df_clean[df_clean['Category'] == category]

        if len(cat_df) < 5:
            continue

        cat_wins = (cat_df[result_col] == wins_value).sum()
        cat_total = len(cat_df)
        cat_acc = (cat_wins / cat_total * 100) if cat_total > 0 else 0

        print(f"{category}: {cat_acc:.1f}% ({cat_wins}/{cat_total})")

    print()
    print("⚠️  Bot does NOT filter by category!")
    print("   Price range is the primary predictor.")
    print()

print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)
print()
print("Summary:")
print(f"  • {total} markets analyzed (all crossed 90%+)")
print(f"  • {overall_acc:.1f}% overall accuracy")
print(f"  • Price ranges defined with real data")
print(f"  • Ready to update config.yaml")
print()
