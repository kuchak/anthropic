"""
Generate comprehensive ranking of ALL subcategories (series)
Including unique market count for each subcategory
"""

import csv
from collections import defaultdict

# Read the comprehensive crossed 90% file
with open('comprehensive_crossed_90_detailed.csv', 'r') as f:
    reader = csv.DictReader(f)

    series_stats = defaultdict(lambda: {
        'category': '',
        'series_title': '',
        'total_events': 0,
        'correct': 0,
        'wrong': 0,
        'markets': set()  # Track unique market IDs
    })

    for row in reader:
        category = row['Category']
        series_ticker = row['Series Ticker']
        series_title = row['Series Title']
        prediction = row['Prediction Correct']
        market_id = row['Ticker']

        series_stats[series_ticker]['category'] = category
        series_stats[series_ticker]['series_title'] = series_title
        series_stats[series_ticker]['total_events'] += 1
        series_stats[series_ticker]['markets'].add(market_id)

        if prediction == 'CORRECT':
            series_stats[series_ticker]['correct'] += 1
        elif prediction == 'WRONG':
            series_stats[series_ticker]['wrong'] += 1

# Calculate success rates - include ALL series with at least 10 events
results = []
for series_ticker, stats in series_stats.items():
    total_events = stats['total_events']

    # Include series with at least 10 events
    if total_events < 10:
        continue

    correct = stats['correct']
    wrong = stats['wrong']
    num_markets = len(stats['markets'])
    success_rate = (correct / total_events * 100) if total_events > 0 else 0

    results.append({
        'category': stats['category'],
        'series_ticker': series_ticker,
        'series_title': stats['series_title'],
        'num_markets': num_markets,
        'total_events': total_events,
        'correct': correct,
        'wrong': wrong,
        'success_rate': success_rate
    })

# Sort by success rate descending, then by total events
results.sort(key=lambda x: (x['success_rate'], x['total_events']), reverse=True)

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
        'Total Events',
        'Wrong',
        'Num Markets'
    ])

    for i, r in enumerate(results, 1):
        writer.writerow([
            i,
            r['category'],
            r['series_title'],
            r['series_ticker'],
            f"{r['success_rate']:.1f}",
            r['correct'],
            r['total_events'],
            r['wrong'],
            r['num_markets']
        ])

print(f"✅ Exported {len(results)} subcategories to all_subcategories_ranked.csv")
print(f"\nMinimum events per subcategory: 10")
print(f"Total events analyzed: {sum(r['total_events'] for r in results)}")
print(f"Total unique markets: {sum(r['num_markets'] for r in results)}")

# Print summary stats
print("\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)

perfect = [r for r in results if r['success_rate'] == 100.0 and r['total_events'] >= 20]
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

print("\n" + "="*100)
print("TOP 50 SUBCATEGORIES")
print("="*100)
print()

for i, r in enumerate(results[:50], 1):
    print(f"{i:3d}. [{r['category']:20s}] {r['series_title'][:45]:45s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_events']:4d})  [{r['num_markets']:3d} mkts]")

print("\n" + "="*100)
print("BOTTOM 20 SUBCATEGORIES")
print("="*100)
print()

for i, r in enumerate(results[-20:], len(results)-19):
    print(f"{i:3d}. [{r['category']:20s}] {r['series_title'][:45]:45s} {r['success_rate']:5.1f}%  ({r['correct']:4d}/{r['total_events']:4d})  [{r['num_markets']:3d} mkts]")

print("\n" + "="*100)

# Show some interesting market depth stats
print("\n" + "="*100)
print("MARKET DEPTH ANALYSIS")
print("="*100)

high_depth = sorted([r for r in results if r['num_markets'] >= 50],
                    key=lambda x: x['num_markets'], reverse=True)[:10]

print("\nSubcategories with MOST unique markets:")
for i, r in enumerate(high_depth, 1):
    events_per_market = r['total_events'] / r['num_markets']
    print(f"{i:2d}. {r['series_title'][:50]:50s} {r['num_markets']:4d} markets, {r['total_events']:4d} events ({events_per_market:.1f} events/market)")

# High reuse markets (same market crossed 90% multiple times)
high_reuse = sorted([r for r in results if r['total_events'] >= 20],
                    key=lambda x: x['total_events'] / x['num_markets'], reverse=True)[:10]

print("\nSubcategories with HIGHEST market reuse (same markets crossing 90% repeatedly):")
for i, r in enumerate(high_reuse, 1):
    events_per_market = r['total_events'] / r['num_markets']
    print(f"{i:2d}. {r['series_title'][:50]:50s} {events_per_market:.1f} events/market ({r['total_events']:4d} events, {r['num_markets']:3d} markets)")

print("\n" + "="*100)
