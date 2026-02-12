"""
Complete breakdown of ALL categories analyzed
Shows EVERY series found and their 90% crossing rates
"""

import json
from collections import defaultdict

# Load the no-time-limit results
with open('comprehensive_kalshi_analysis.json', 'r') as f:
    data = json.load(f)

series_results = data['series_results']

print("="*100)
print("COMPLETE ANALYSIS - ALL CATEGORIES & SERIES")
print("="*100)
print(f"\nTotal series analyzed: {len(series_results)}")

# Group by category
by_category = defaultdict(list)
for result in series_results:
    by_category[result['category']].append(result)

# Sort categories by number of series
categories_sorted = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

print(f"\nTotal categories found: {len(categories_sorted)}")
print("\n" + "="*100)
print("BREAKDOWN BY CATEGORY")
print("="*100)

for category, results in categories_sorted:
    # Calculate category stats
    total_events = sum(r['events_analyzed'] for r in results)
    total_crossed = sum(r['crossed_90'] for r in results)

    # Count how many series have significant crossings (50+)
    series_with_50_plus = len([r for r in results if r['crossed_90'] >= 50])
    series_with_20_plus = len([r for r in results if r['crossed_90'] >= 20])
    series_with_any = len([r for r in results if r['crossed_90'] > 0])

    print(f"\n{'='*100}")
    print(f"📂 {category.upper()}")
    print(f"{'='*100}")
    print(f"Series in category: {len(results)}")
    print(f"Total events analyzed: {total_events}")
    print(f"Total events that crossed 90%: {total_crossed}")
    print(f"Average crossing rate: {total_crossed/total_events*100:.1f}%")
    print(f"\nSeries with 50+ crossings: {series_with_50_plus}")
    print(f"Series with 20+ crossings: {series_with_20_plus}")
    print(f"Series with ANY crossings: {series_with_any}")

    # Sort series by crossing rate
    results_sorted = sorted(results, key=lambda x: x['crossing_rate'], reverse=True)

    print(f"\n{'Series Ticker':<30} {'Events':<10} {'Crossed':<15} {'Cross %':<12} {'Accuracy':<12}")
    print("-"*100)

    for result in results_sorted:
        ticker = result['series_ticker'][:28]
        events = result['events_analyzed']
        crossed = result['crossed_90']
        crossed_str = f"{crossed}/{events}"
        cross_pct = f"{result['crossing_rate']:.1f}%"
        accuracy = f"{result['accuracy']:.1f}%" if crossed > 0 else "N/A"

        # Mark significant series
        marker = ""
        if crossed >= 50:
            marker = "🟢"
        elif crossed >= 20:
            marker = "🟡"
        elif crossed > 0:
            marker = "⚪"
        else:
            marker = "🔴"

        print(f"{ticker:<30} {events:<10d} {crossed_str:<15} {cross_pct:<12} {accuracy:<12} {marker}")

# Summary table
print("\n" + "="*100)
print("CATEGORY SUMMARY TABLE")
print("="*100)
print(f"\n{'Category':<25} {'Series':<10} {'Events':<12} {'Crossed':<12} {'Cross %':<12} {'50+ Series':<12} {'20+ Series'}")
print("-"*100)

for category, results in categories_sorted:
    total_events = sum(r['events_analyzed'] for r in results)
    total_crossed = sum(r['crossed_90'] for r in results)
    series_with_50_plus = len([r for r in results if r['crossed_90'] >= 50])
    series_with_20_plus = len([r for r in results if r['crossed_90'] >= 20])

    cat_name = category[:23]
    series_count = len(results)
    cross_pct = f"{total_crossed/total_events*100:.1f}%" if total_events > 0 else "0%"

    print(f"{cat_name:<25} {series_count:<10d} {total_events:<12d} {total_crossed:<12d} {cross_pct:<12} {series_with_50_plus:<12d} {series_with_20_plus:<12d}")

print("\n" + "="*100)
print("KEY:")
print("🟢 = 50+ crossings (reliable for trading)")
print("🟡 = 20-49 crossings (moderate data)")
print("⚪ = 1-19 crossings (insufficient data)")
print("🔴 = 0 crossings (never crossed 90%)")
print("="*100)
