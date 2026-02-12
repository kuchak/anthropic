"""
Export all analysis results to organized CSV files
"""

import json
import csv
from collections import defaultdict

# Load results
with open('comprehensive_kalshi_analysis.json', 'r') as f:
    data = json.load(f)

series_results = data['series_results']

print("Exporting to CSV files...")

# 1. CATEGORY SUMMARY CSV
print("\n1. Creating category_summary.csv...")
by_category = defaultdict(list)
for result in series_results:
    by_category[result['category']].append(result)

with open('category_summary.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Category',
        'Total_Series',
        'Total_Events_Analyzed',
        'Total_Events_Crossed_90',
        'Avg_Crossing_Rate_Pct',
        'Series_With_50_Plus_Crossings',
        'Series_With_20_Plus_Crossings',
        'Total_Correct_Predictions',
        'Overall_Accuracy_Pct',
        'Avg_Betting_Window_Minutes'
    ])

    for category, results in sorted(by_category.items(), key=lambda x: sum(r['crossed_90'] for r in x[1]), reverse=True):
        total_series = len(results)
        total_events = sum(r['events_analyzed'] for r in results)
        total_crossed = sum(r['crossed_90'] for r in results)
        avg_crossing_rate = (total_crossed / total_events * 100) if total_events > 0 else 0
        series_50_plus = len([r for r in results if r['crossed_90'] >= 50])
        series_20_plus = len([r for r in results if r['crossed_90'] >= 20])
        total_correct = sum(r['correct_predictions'] for r in results)
        overall_accuracy = (total_correct / total_crossed * 100) if total_crossed > 0 else 0
        avg_window = sum(r['avg_betting_window'] for r in results) / len(results) if results else 0

        writer.writerow([
            category,
            total_series,
            total_events,
            total_crossed,
            f"{avg_crossing_rate:.2f}",
            series_50_plus,
            series_20_plus,
            total_correct,
            f"{overall_accuracy:.2f}",
            f"{avg_window:.2f}"
        ])

print(f"✅ Created category_summary.csv ({len(by_category)} categories)")

# 2. ALL SERIES DETAILED CSV
print("\n2. Creating all_series_detailed.csv...")
with open('all_series_detailed.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Series_Ticker',
        'Series_Title',
        'Category',
        'Events_Analyzed',
        'Events_Crossed_90',
        'Crossing_Rate_Pct',
        'Correct_Predictions',
        'Incorrect_Predictions',
        'Accuracy_Pct',
        'Avg_Betting_Window_Minutes',
        'Reliability_Tier'
    ])

    for result in sorted(series_results, key=lambda x: x['accuracy'], reverse=True):
        crossed = result['crossed_90']

        # Determine reliability tier
        if crossed >= 50:
            tier = 'HIGH (50+)'
        elif crossed >= 20:
            tier = 'MEDIUM (20-49)'
        elif crossed > 0:
            tier = 'LOW (1-19)'
        else:
            tier = 'NONE (0)'

        writer.writerow([
            result['series_ticker'],
            result['series_title'],
            result['category'],
            result['events_analyzed'],
            result['crossed_90'],
            f"{result['crossing_rate']:.2f}",
            result['correct_predictions'],
            result['crossed_90'] - result['correct_predictions'],
            f"{result['accuracy']:.2f}",
            f"{result['avg_betting_window']:.2f}",
            tier
        ])

print(f"✅ Created all_series_detailed.csv ({len(series_results)} series)")

# 3. TOP PERFORMERS CSV (50+ crossings only)
print("\n3. Creating top_performers.csv...")
top_performers = [r for r in series_results if r['crossed_90'] >= 50]
top_performers_sorted = sorted(top_performers, key=lambda x: x['accuracy'], reverse=True)

with open('top_performers.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Rank',
        'Series_Ticker',
        'Series_Title',
        'Category',
        'Events_Analyzed',
        'Events_Crossed_90',
        'Crossing_Rate_Pct',
        'Correct_Predictions',
        'Accuracy_Pct',
        'Avg_Betting_Window_Minutes'
    ])

    for i, result in enumerate(top_performers_sorted, 1):
        writer.writerow([
            i,
            result['series_ticker'],
            result['series_title'],
            result['category'],
            result['events_analyzed'],
            result['crossed_90'],
            f"{result['crossing_rate']:.2f}",
            result['correct_predictions'],
            f"{result['accuracy']:.2f}",
            f"{result['avg_betting_window']:.2f}"
        ])

print(f"✅ Created top_performers.csv ({len(top_performers)} series)")

# 4. CATEGORY-SPECIFIC CSVs (for major categories)
print("\n4. Creating category-specific CSVs...")

for category, results in by_category.items():
    if len(results) >= 5:  # Only create if 5+ series
        filename = f"category_{category.lower().replace(' ', '_').replace('/', '_')}.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Series_Ticker',
                'Series_Title',
                'Events_Analyzed',
                'Events_Crossed_90',
                'Crossing_Rate_Pct',
                'Correct_Predictions',
                'Accuracy_Pct',
                'Avg_Betting_Window_Minutes'
            ])

            for result in sorted(results, key=lambda x: x['accuracy'], reverse=True):
                writer.writerow([
                    result['series_ticker'],
                    result['series_title'],
                    result['events_analyzed'],
                    result['crossed_90'],
                    f"{result['crossing_rate']:.2f}",
                    result['correct_predictions'],
                    f"{result['accuracy']:.2f}",
                    f"{result['avg_betting_window']:.2f}"
                ])

        print(f"  ✅ {filename} ({len(results)} series)")

# 5. COMPARISON CSV (4-hour vs No time limit)
print("\n5. Creating comparison_4hr_vs_unlimited.csv...")
# This would require loading both JSON files if we had both versions
# For now, just note which analysis was used

print("\n" + "="*70)
print("📊 CSV EXPORT COMPLETE!")
print("="*70)
print("\nFiles created:")
print("1. category_summary.csv - High-level category statistics")
print("2. all_series_detailed.csv - Complete series breakdown")
print("3. top_performers.csv - Series with 50+ crossings (ranked by accuracy)")
print("4. category_*.csv - Individual files for each major category")
print("="*70)
