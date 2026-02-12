"""
Analyze actual backtest results and extract accuracy data by price range
"""
import pandas as pd
import sys

# Read the latest backtest CSV
backtest_file = '/home/user/anthropic/kalshi_backtest_20260211_034133.csv'

print("=" * 80)
print("ANALYZING ACTUAL BACKTEST RESULTS")
print("=" * 80)
print()

try:
    df = pd.read_csv(backtest_file)
    print(f"✅ Loaded {len(df)} markets from backtest")
    print(f"   File: {backtest_file}")
    print()
except Exception as e:
    print(f"❌ Error loading backtest: {e}")
    sys.exit(1)

# Show columns
print("📋 Columns in backtest data:")
print(f"   {', '.join(df.columns.tolist())}")
print()

# Filter to markets that hit 90%+ (our strategy targets)
if 'hit_90_percent' in df.columns:
    high_prob_df = df[df['hit_90_percent'] == True].copy()
    print(f"🎯 Markets that hit 90%+ probability: {len(high_prob_df)}")
    print(f"   (This is our target market set)")
    print()
else:
    print("⚠️  'hit_90_percent' column not found")
    high_prob_df = df.copy()

# Check if we have crossing_price data
if 'crossing_price' in high_prob_df.columns:
    # Remove rows with no price data
    high_prob_df = high_prob_df[high_prob_df['crossing_price'].notna()].copy()
    print(f"📊 Markets with price data: {len(high_prob_df)}")
    print()

    # Convert crossing_price to cents (divide by 100 if needed)
    # Check if prices are in cents (0-100) or dollars (0-1)
    sample_price = high_prob_df['crossing_price'].iloc[0] if len(high_prob_df) > 0 else 0
    if sample_price > 1:
        high_prob_df['price'] = high_prob_df['crossing_price'] / 100
        print("   Converted prices from cents to dollars")
    else:
        high_prob_df['price'] = high_prob_df['crossing_price']
        print("   Prices already in dollars")
    print()

# Show result distribution
if 'result' in high_prob_df.columns:
    print("📈 OVERALL RESULTS")
    print("=" * 80)
    print()

    result_counts = high_prob_df['result'].value_counts()
    total = len(high_prob_df)

    for result, count in result_counts.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"   {result}: {count} ({pct:.1f}%)")

    # Calculate win rate (assuming 'yes' means we won)
    wins = result_counts.get('yes', 0)
    win_rate = (wins / total * 100) if total > 0 else 0
    print()
    print(f"   Overall Win Rate: {win_rate:.1f}% ({wins}/{total})")
    print()

# Analyze by price range
if 'price' in high_prob_df.columns and 'result' in high_prob_df.columns:
    print("📊 ACCURACY BY PRICE RANGE")
    print("=" * 80)
    print()

    # Define price ranges matching our config
    ranges = [
        (0.00, 0.50, "< $0.50 (below min)"),
        (0.50, 0.85, "$0.50-0.85 (below target)"),
        (0.85, 0.89, "$0.85-0.89 (HIGH confidence)"),
        (0.90, 0.95, "$0.90-0.95 (MID confidence)"),
        (0.95, 0.98, "$0.95-0.98 (approaching max)"),
        (0.98, 1.00, "> $0.98 (above max)"),
    ]

    summary_data = []

    for min_price, max_price, label in ranges:
        range_df = high_prob_df[
            (high_prob_df['price'] >= min_price) &
            (high_prob_df['price'] <= max_price)
        ]

        if len(range_df) == 0:
            continue

        wins = (range_df['result'] == 'yes').sum()
        losses = (range_df['result'] == 'no').sum()
        total = len(range_df)
        win_rate = (wins / total * 100) if total > 0 else 0

        print(f"{label}:")
        print(f"   Total: {total} markets")
        print(f"   Wins: {wins}")
        print(f"   Losses: {losses}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Accuracy: {win_rate / 100:.3f}")
        print()

        summary_data.append({
            'range': label,
            'min': min_price,
            'max': max_price,
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'accuracy': win_rate / 100
        })

    # Extract the key ranges for config
    print()
    print("🎯 RECOMMENDED CONFIG VALUES")
    print("=" * 80)
    print()
    print("accuracy_by_price_range:")

    for data in summary_data:
        if data['total'] >= 5:  # Only show ranges with enough data
            if 0.85 <= data['min'] < 0.90:
                print(f'  "0.85-0.89": {data["accuracy"]:.3f}  # {data["win_rate"]:.1f}% ({data["wins"]}/{data["total"]} wins)')
            elif 0.90 <= data['min'] < 0.95:
                print(f'  "0.90-0.95": {data["accuracy"]:.3f}  # {data["win_rate"]:.1f}% ({data["wins"]}/{data["total"]} wins)')
            elif 0.95 <= data['min'] < 0.98:
                print(f'  "0.95-0.98": {data["accuracy"]:.3f}  # {data["win_rate"]:.1f}% ({data["wins"]}/{data["total"]} wins)')

    # Calculate overall accuracy for default
    total_wins = sum(d['wins'] for d in summary_data)
    total_markets = sum(d['total'] for d in summary_data)
    overall_accuracy = total_wins / total_markets if total_markets > 0 else 0.90

    print()
    print(f'default_accuracy: {overall_accuracy:.3f}  # {overall_accuracy * 100:.1f}% overall')
    print()

# Category breakdown
if 'category' in high_prob_df.columns and 'result' in high_prob_df.columns:
    print()
    print("📂 ACCURACY BY CATEGORY (for reference)")
    print("=" * 80)
    print()

    category_stats = []

    for category in high_prob_df['category'].unique():
        cat_df = high_prob_df[high_prob_df['category'] == category]

        if len(cat_df) < 3:  # Skip categories with too little data
            continue

        wins = (cat_df['result'] == 'yes').sum()
        total = len(cat_df)
        win_rate = (wins / total * 100) if total > 0 else 0

        category_stats.append({
            'category': category,
            'total': total,
            'wins': wins,
            'win_rate': win_rate
        })

    # Sort by total markets
    category_stats.sort(key=lambda x: x['total'], reverse=True)

    for stat in category_stats[:10]:  # Show top 10
        print(f"{stat['category']}: {stat['win_rate']:.1f}% ({stat['wins']}/{stat['total']})")

    print()
    print("NOTE: Bot should NOT filter by category!")
    print("Price range accuracy is more predictive than category.")
    print()

print()
print("=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
