"""
Analyze the 30 false positives to find patterns
Goal: Identify filters to improve 93.7% → closer to 100%
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime

# Load the analysis results
with open('tennis_500_matches_analysis.json', 'r') as f:
    data = json.load(f)

matches = data['matches']

# Split into correct vs false positives
correct_predictions = [m for m in matches if m['prediction_correct']]
false_positives = [m for m in matches if not m['prediction_correct']]

print("="*70)
print("🔍 FALSE POSITIVE ANALYSIS")
print("="*70)
print(f"\nTotal matches that crossed 90%: {len(matches)}")
print(f"Correct: {len(correct_predictions)} (93.7%)")
print(f"False positives: {len(false_positives)} (6.3%)")

# === ANALYSIS 1: Round Type ===
print("\n" + "="*70)
print("📊 ANALYSIS 1: Round Type")
print("="*70)

def extract_round_type(title):
    """Extract round type from title"""
    title_lower = title.lower()

    if 'qualification' in title_lower or 'qualifying' in title_lower:
        return 'Qualifying'
    elif 'final' in title_lower and 'round' not in title_lower:
        if 'semi' in title_lower:
            return 'Semi-Final'
        elif 'quarter' in title_lower:
            return 'Quarter-Final'
        else:
            return 'Final'
    elif 'round of 128' in title_lower:
        return 'Round of 128'
    elif 'round of 64' in title_lower:
        return 'Round of 64'
    elif 'round of 32' in title_lower:
        return 'Round of 32'
    elif 'round of 16' in title_lower:
        return 'Round of 16'
    else:
        return 'Other'

# Count by round type
false_pos_rounds = Counter([extract_round_type(m['title']) for m in false_positives])
correct_rounds = Counter([extract_round_type(m['title']) for m in correct_predictions])

print("\nFalse Positives by Round:")
for round_type, count in false_pos_rounds.most_common():
    total_in_round = count + correct_rounds.get(round_type, 0)
    error_rate = count / total_in_round * 100 if total_in_round > 0 else 0
    print(f"  {round_type:20s}: {count:2d}/{total_in_round:3d} = {error_rate:5.1f}% error rate")

# === ANALYSIS 2: Price Level ===
print("\n" + "="*70)
print("📊 ANALYSIS 2: Price When Crossed 90%")
print("="*70)

def price_bucket(price):
    """Bucket prices"""
    if price >= 95:
        return '95-100¢'
    elif price >= 92:
        return '92-94¢'
    elif price >= 90:
        return '90-91¢'
    else:
        return '<90¢'

false_pos_prices = Counter([price_bucket(m['first_touch']['price']) for m in false_positives])
correct_prices = Counter([price_bucket(m['first_touch']['price']) for m in correct_predictions])

print("\nFalse Positives by Price Level:")
for price_range in ['95-100¢', '92-94¢', '90-91¢']:
    fp_count = false_pos_prices.get(price_range, 0)
    correct_count = correct_prices.get(price_range, 0)
    total = fp_count + correct_count
    error_rate = fp_count / total * 100 if total > 0 else 0
    print(f"  {price_range:10s}: {fp_count:2d}/{total:3d} = {error_rate:5.1f}% error rate")

# === ANALYSIS 3: Betting Window ===
print("\n" + "="*70)
print("📊 ANALYSIS 3: Betting Window Length")
print("="*70)

def window_bucket(minutes):
    """Bucket betting windows"""
    if minutes is None:
        return 'Unknown'
    elif minutes >= 120:
        return '120+ min'
    elif minutes >= 60:
        return '60-120 min'
    elif minutes >= 30:
        return '30-60 min'
    elif minutes >= 15:
        return '15-30 min'
    else:
        return '<15 min'

false_pos_windows = Counter([window_bucket(m['betting_window_minutes']) for m in false_positives])
correct_windows = Counter([window_bucket(m['betting_window_minutes']) for m in correct_predictions])

print("\nFalse Positives by Betting Window:")
for window in ['<15 min', '15-30 min', '30-60 min', '60-120 min', '120+ min']:
    fp_count = false_pos_windows.get(window, 0)
    correct_count = correct_windows.get(window, 0)
    total = fp_count + correct_count
    error_rate = fp_count / total * 100 if total > 0 else 0
    print(f"  {window:12s}: {fp_count:2d}/{total:3d} = {error_rate:5.1f}% error rate")

# === ANALYSIS 4: Individual False Positives ===
print("\n" + "="*70)
print("📋 DETAILED FALSE POSITIVES")
print("="*70)

# Sort by price (highest first)
false_positives_sorted = sorted(false_positives, key=lambda x: x['first_touch']['price'], reverse=True)

for i, m in enumerate(false_positives_sorted, 1):
    round_type = extract_round_type(m['title'])
    price = m['first_touch']['price']
    window = m['betting_window_minutes']

    print(f"\n{i}. {m['ticker']}")
    print(f"   Title: {m['title'][:60]}...")
    print(f"   Round: {round_type}")
    print(f"   Price: {price}¢")
    print(f"   Window: {window:.1f} min" if window else "   Window: N/A")
    print(f"   Crossed: {m['first_touch']['timestamp']}")

# === ANALYSIS 5: Combined Filters ===
print("\n" + "="*70)
print("🎯 FILTER RECOMMENDATIONS")
print("="*70)

# Test different filter combinations
filters_to_test = [
    {
        'name': 'No Qualifying Rounds',
        'filter': lambda m: extract_round_type(m['title']) != 'Qualifying'
    },
    {
        'name': 'Price >= 92¢',
        'filter': lambda m: m['first_touch']['price'] >= 92
    },
    {
        'name': 'Price >= 95¢',
        'filter': lambda m: m['first_touch']['price'] >= 95
    },
    {
        'name': 'Window < 90 min',
        'filter': lambda m: m['betting_window_minutes'] and m['betting_window_minutes'] < 90
    },
    {
        'name': 'No Qualifying + Price >= 92¢',
        'filter': lambda m: extract_round_type(m['title']) != 'Qualifying' and m['first_touch']['price'] >= 92
    },
    {
        'name': 'No Qualifying + Price >= 95¢',
        'filter': lambda m: extract_round_type(m['title']) != 'Qualifying' and m['first_touch']['price'] >= 95
    },
]

print("\nTesting filter combinations:\n")

for filter_config in filters_to_test:
    name = filter_config['name']
    filter_fn = filter_config['filter']

    # Apply filter
    filtered_correct = [m for m in correct_predictions if filter_fn(m)]
    filtered_false_pos = [m for m in false_positives if filter_fn(m)]

    total_filtered = len(filtered_correct) + len(filtered_false_pos)
    accuracy = len(filtered_correct) / total_filtered * 100 if total_filtered > 0 else 0

    print(f"{name:35s}: {len(filtered_correct):3d}/{total_filtered:3d} = {accuracy:5.1f}% accuracy ({len(filtered_false_pos)} FP)")

# === SUMMARY ===
print("\n" + "="*70)
print("💡 KEY INSIGHTS")
print("="*70)

print("""
Based on the analysis above, we can improve accuracy by:

1. FILTERING BY ROUND TYPE
   - Qualifying rounds appear riskier
   - Consider filtering them out

2. FILTERING BY PRICE LEVEL
   - Higher prices (95¢+) are more reliable
   - 90-91¢ crossings are riskier

3. FILTERING BY BETTING WINDOW
   - Very long windows (2+ hours) may indicate early/uncertain predictions
   - Shorter windows suggest late-match dominance

4. COMBINATION FILTERS
   - Best balance: accuracy vs opportunity count
   - Test these on live data before deploying
""")

print("="*70)
