"""
Generate comprehensive ranking of ALL subcategories (series)
Including all sports leagues and market types
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

# Calculate success rates - include ALL series with at least 10 events
results = []
for series_ticker, stats in series_stats.items():
    total = stats['total']

    # Include series with at least 10 events
    if total < 10:
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

# Sort by success rate descending, then by total events
results.sort(key=lambda x: (x['success_rate'], x['total_crossed_90']), reverse=True)

# Write to CSV
with open('all_subcategories_ranked.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Rank',
        'Category',
        'Subcategory',
        'Series Ticker',
        'Success Rate (%)',
        'Correct',
        'Total Crossed 90%',
        'Wrong'
    ])

    for i, r in enumerate(results, 1):
        writer.writerow([
            i,
            r['category'],
            r['series_title'],
            r['series_ticker'],
            f"{r['success_rate']:.1f}",
            r['correct'],
            r['total_crossed_90'],
            r['wrong']
        ])

print(f"✅ Exported {len(results)} subcategories to all_subcategories_ranked.csv")
print(f"\nMinimum events per subcategory: 10")
print(f"Total events analyzed: {sum(r['total_crossed_90'] for r in results)}")

# Print summary stats
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

perfect = [r for r in results if r['success_rate'] == 100.0 and r['total_crossed_90'] >= 20]
great = [r for r in results if r['success_rate'] >= 95.0 and r['success_rate'] < 100.0]
good = [r for r in results if r['success_rate'] >= 90.0 and r['success_rate'] < 95.0]
decent = [r for r in results if r['success_rate'] >= 85.0 and r['success_rate'] < 90.0]
fair = [r for r in results if r['success_rate'] >= 80.0 and r['success_rate'] < 85.0]
poor = [r for r in results if r['success_rate'] < 80.0]

print(f"\n🏆 Perfect (100%, 20+ events): {len(perfect)} subcategories")
print(f"💎 Great (95-99%): {len(great)} subcategories")
print(f"✅ Good (90-95%): {len(good)} subcategories")
print(f"👍 Decent (85-90%): {len(decent)} subcategories")
print(f"📊 Fair (80-85%): {len(fair)} subcategories")
print(f"⚠️  Poor (<80%): {len(poor)} subcategories")

print("\n" + "="*80)
print("TOP 50 SUBCATEGORIES")
print("="*80)
print()

for i, r in enumerate(results[:50], 1):
    print(f"{i:3d}. [{r['category']:20s}] {r['series_title'][:55]:55s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_crossed_90']:4d})")

print("\n" + "="*80)
print("BOTTOM 20 SUBCATEGORIES")
print("="*80)
print()

for i, r in enumerate(results[-20:], len(results)-19):
    print(f"{i:3d}. [{r['category']:20s}] {r['series_title'][:55]:55s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_crossed_90']:4d})")

print("\n" + "="*80)
