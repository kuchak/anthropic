"""
Display ALL categories with their accuracy ratings
"""

import json
from collections import defaultdict

# Load results
with open('comprehensive_kalshi_analysis.json', 'r') as f:
    data = json.load(f)

series_results = data['series_results']

# Filter for series with at least 50 events that crossed 90%
significant_results = [r for r in series_results if r['crossed_90'] >= 50]

print("="*90)
print("📊 ALL SERIES WITH 50+ EVENTS THAT CROSSED 90%")
print("="*90)
print(f"\nTotal series analyzed: {len(series_results)}")
print(f"Series with 50+ crossings: {len(significant_results)}")

# Group by category
category_stats = defaultdict(list)

for result in significant_results:
    category_stats[result['category']].append(result)

# Calculate category summaries
category_summary = []

for category, results in category_stats.items():
    total_crossed = sum(r['crossed_90'] for r in results)
    total_correct = sum(r['correct_predictions'] for r in results)
    avg_accuracy = total_correct / total_crossed * 100 if total_crossed > 0 else 0
    avg_window = sum(r['avg_betting_window'] for r in results) / len(results)
    avg_crossing_rate = sum(r['crossing_rate'] for r in results) / len(results)

    category_summary.append({
        'category': category,
        'series_count': len(results),
        'total_crossed': total_crossed,
        'total_events': sum(r['events_analyzed'] for r in results),
        'accuracy': avg_accuracy,
        'avg_window': avg_window,
        'avg_crossing_rate': avg_crossing_rate
    })

# Sort by accuracy
category_summary_sorted = sorted(category_summary, key=lambda x: x['accuracy'], reverse=True)

print("\n" + "="*90)
print("📊 CATEGORY PERFORMANCE RANKINGS")
print("="*90)
print(f"\n{'Rank':<6} {'Category':<25} {'Series':<8} {'Events':<10} {'Crossed':<10} {'Cross %':<10} {'Accuracy':<12} {'Avg Window'}")
print("-"*110)

for i, cat in enumerate(category_summary_sorted, 1):
    rank = f"#{i}"
    cat_name = cat['category'][:23]
    series_count = cat['series_count']
    total_events = cat['total_events']
    crossed = cat['total_crossed']
    cross_pct = f"{cat['avg_crossing_rate']:.1f}%"
    accuracy = f"{cat['accuracy']:.1f}%"
    window = f"{cat['avg_window']:.1f}m"

    print(f"{rank:<6} {cat_name:<25} {series_count:<8d} {total_events:<10d} {crossed:<10d} {cross_pct:<10} {accuracy:<12} {window}")

print("\n" + "="*90)
print("📊 ALL SERIES BY CATEGORY (Sorted by Accuracy)")
print("="*90)

for cat_summary in category_summary_sorted:
    category = cat_summary['category']
    results = category_stats[category]

    # Sort series within category by accuracy
    results_sorted = sorted(results, key=lambda x: x['accuracy'], reverse=True)

    print(f"\n{'='*90}")
    print(f"📂 {category.upper()}")
    print(f"   {cat_summary['series_count']} series | {cat_summary['total_crossed']} crossed 90% | {cat_summary['accuracy']:.1f}% avg accuracy")
    print(f"{'='*90}")
    print(f"{'Series':<30} {'Events':<10} {'Crossed':<12} {'Cross %':<10} {'Accuracy':<10} {'Window'}")
    print("-"*90)

    for result in results_sorted:
        series = result['series_ticker'][:28]
        events = result['events_analyzed']
        crossed = result['crossed_90']
        crossed_str = f"{crossed}/{events}"
        cross_pct = f"{result['crossing_rate']:.1f}%"
        accuracy = f"{result['accuracy']:.1f}%"
        window = f"{result['avg_betting_window']:.1f}m"

        # Add emoji for top performers
        emoji = ""
        if result['accuracy'] >= 99:
            emoji = "🥇"
        elif result['accuracy'] >= 95:
            emoji = "🥈"
        elif result['accuracy'] >= 90:
            emoji = "🥉"

        print(f"{series:<30} {events:<10d} {crossed_str:<12} {cross_pct:<10} {accuracy:<10} {window:<10} {emoji}")

print("\n" + "="*90)
print("📊 SERIES WITH FEWER THAN 50 CROSSINGS (Not recommended)")
print("="*90)

low_volume_results = [r for r in series_results if r['crossed_90'] < 50 and r['crossed_90'] > 0]
low_volume_results_sorted = sorted(low_volume_results, key=lambda x: x['accuracy'], reverse=True)

print(f"\n{'Series':<30} {'Category':<20} {'Events':<10} {'Crossed':<12} {'Accuracy'}")
print("-"*90)

for result in low_volume_results_sorted[:50]:  # Show top 50
    series = result['series_ticker'][:28]
    category = result['category'][:18]
    events = result['events_analyzed']
    crossed = result['crossed_90']
    crossed_str = f"{crossed}/{events}"
    accuracy = f"{result['accuracy']:.1f}%"

    print(f"{series:<30} {category:<20} {events:<10d} {crossed_str:<12} {accuracy}")

print("\n" + "="*90)
