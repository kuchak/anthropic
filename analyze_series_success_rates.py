"""
Analyze success rates by series (subcategories) within each category
Find the most reliable specific market types
"""

import csv
from collections import defaultdict

# Read the comprehensive crossed 90% file
with open('comprehensive_crossed_90_detailed.csv', 'r') as f:
    reader = csv.DictReader(f)

    series_stats = defaultdict(lambda: {
        'category': '',
        'series_title': '',
        'total': 0,
        'correct': 0,
        'wrong': 0
    })

    for row in reader:
        category = row['Category']
        series_ticker = row['Series Ticker']
        series_title = row['Series Title']
        prediction = row['Prediction Correct']

        series_stats[series_ticker]['category'] = category
        series_stats[series_ticker]['series_title'] = series_title
        series_stats[series_ticker]['total'] += 1

        if prediction == 'CORRECT':
            series_stats[series_ticker]['correct'] += 1
        elif prediction == 'WRONG':
            series_stats[series_ticker]['wrong'] += 1

# Calculate success rates and filter for meaningful sample sizes
results = []
for series_ticker, stats in series_stats.items():
    total = stats['total']

    # Only include series with at least 20 events for statistical significance
    if total < 20:
        continue

    correct = stats['correct']
    wrong = stats['wrong']
    success_rate = (correct / total * 100) if total > 0 else 0

    results.append({
        'category': stats['category'],
        'series_ticker': series_ticker,
        'series_title': stats['series_title'],
        'total_crossed_90': total,
        'correct': correct,
        'wrong': wrong,
        'success_rate': success_rate
    })

# Sort by success rate descending
results.sort(key=lambda x: x['success_rate'], reverse=True)

# Print overall top performers
print("=" * 100)
print("TOP 30 MOST RELIABLE SERIES (Subcategories)")
print("Minimum 20 events that crossed 90%")
print("=" * 100)
print()

for i, r in enumerate(results[:30], 1):
    print(f"{i:2d}. [{r['category']:20s}] {r['series_title']:45s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_crossed_90']:4d})  [{r['wrong']:3d} wrong]")

print("\n" + "=" * 100)

# Now show best subcategories within each major category
print("\n" + "=" * 100)
print("BEST SUBCATEGORIES WITHIN EACH MAJOR CATEGORY")
print("=" * 100)

# Group by category
by_category = defaultdict(list)
for r in results:
    by_category[r['category']].append(r)

# Show top 3 series per category
for category in sorted(by_category.keys()):
    series_list = by_category[category]
    series_list.sort(key=lambda x: x['success_rate'], reverse=True)

    print(f"\n📊 {category.upper()}")
    print("-" * 100)

    for i, r in enumerate(series_list[:3], 1):
        print(f"  {i}. {r['series_title']:50s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_crossed_90']:4d})")

print("\n" + "=" * 100)
