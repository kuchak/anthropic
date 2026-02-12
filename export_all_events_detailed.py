"""
Export ALL events in the same format as tennis_90_crossing_detailed.csv
One row per event across all categories
"""

import json
import csv
from datetime import datetime

# Load results
with open('comprehensive_kalshi_analysis.json', 'r') as f:
    data = json.load(f)

series_results = data['series_results']

print("Exporting all events to detailed CSV format...")
print(f"Processing {len(series_results)} series...")

all_events = []
events_crossed_90 = []

for series_result in series_results:
    for event in series_result['events']:
        all_events.append({
            'category': series_result['category'],
            'series_ticker': series_result['series_ticker'],
            'series_title': series_result['series_title'],
            **event
        })

        if event['crossed_90']:
            events_crossed_90.append({
                'category': series_result['category'],
                'series_ticker': series_result['series_ticker'],
                'series_title': series_result['series_title'],
                **event
            })

print(f"\nTotal events: {len(all_events)}")
print(f"Events that crossed 90%: {len(events_crossed_90)}")

# 1. ALL EVENTS DETAILED (matches tennis_500_matches_detailed.csv format)
print("\n1. Creating all_events_detailed.csv...")
with open('all_events_detailed.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Category',
        'Series Ticker',
        'Series Title',
        'Ticker',
        'Title',
        'Result',
        'Settlement (¢)',
        'Crossed 90%',
        'First Touch Time',
        'First Touch Price (¢)',
        'Permanent Cross Time',
        'Permanent Cross Price (¢)',
        'Market Close Time',
        'Betting Window (min)',
        'Betting Window (sec)',
        'Prediction Correct',
        'Trades Count'
    ])

    for event in all_events:
        writer.writerow([
            event['category'],
            event['series_ticker'],
            event['series_title'],
            event['ticker'],
            event['title'],
            event['result'],
            event['settlement_price'],
            'YES' if event['crossed_90'] else 'NO',
            event.get('first_touch_time', ''),
            event.get('first_touch_price', ''),
            event.get('permanent_cross_time', ''),
            event.get('permanent_cross_price', ''),
            event['close_time'],
            f"{event['betting_window']:.1f}" if event.get('betting_window') else '',
            f"{int(event['betting_window'] * 60)}" if event.get('betting_window') else '',
            event.get('prediction_correct', ''),
            event['trades_count']
        ])

print(f"✅ Created all_events_detailed.csv ({len(all_events)} events)")

# 2. ONLY EVENTS THAT CROSSED 90% (matches tennis_90_crossing_detailed.csv format)
print("\n2. Creating events_crossed_90_detailed.csv...")
with open('events_crossed_90_detailed.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Category',
        'Series Ticker',
        'Series Title',
        'Ticker',
        'Title',
        'Result',
        'Settlement (¢)',
        'Crossed 90%',
        'First Touch Time',
        'First Touch Price (¢)',
        'Permanent Cross Time',
        'Permanent Cross Price (¢)',
        'Market Close Time',
        'Betting Window (min)',
        'Betting Window (sec)',
        'Prediction Correct',
        'Trades Count'
    ])

    for event in events_crossed_90:
        writer.writerow([
            event['category'],
            event['series_ticker'],
            event['series_title'],
            event['ticker'],
            event['title'],
            event['result'],
            event['settlement_price'],
            'YES',
            event['first_touch_time'],
            event['first_touch_price'],
            event['permanent_cross_time'],
            event['permanent_cross_price'],
            event['close_time'],
            f"{event['betting_window']:.1f}",
            f"{int(event['betting_window'] * 60)}",
            event['prediction_correct'],
            event['trades_count']
        ])

print(f"✅ Created events_crossed_90_detailed.csv ({len(events_crossed_90)} events)")

# 3. CATEGORY BREAKDOWN FILES (same format)
print("\n3. Creating per-category event files...")

by_category = {}
for event in events_crossed_90:
    cat = event['category']
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(event)

for category, events in by_category.items():
    if len(events) >= 10:  # Only create if 10+ events crossed
        filename = f"events_{category.lower().replace(' ', '_').replace('/', '_')}_90crossing.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Series Ticker',
                'Series Title',
                'Ticker',
                'Title',
                'Result',
                'Settlement (¢)',
                'First Touch Time',
                'First Touch Price (¢)',
                'Permanent Cross Time',
                'Permanent Cross Price (¢)',
                'Market Close Time',
                'Betting Window (min)',
                'Betting Window (sec)',
                'Prediction Correct',
                'Trades Count'
            ])

            for event in events:
                writer.writerow([
                    event['series_ticker'],
                    event['series_title'],
                    event['ticker'],
                    event['title'],
                    event['result'],
                    event['settlement_price'],
                    event['first_touch_time'],
                    event['first_touch_price'],
                    event['permanent_cross_time'],
                    event['permanent_cross_price'],
                    event['close_time'],
                    f"{event['betting_window']:.1f}",
                    f"{int(event['betting_window'] * 60)}",
                    event['prediction_correct'],
                    event['trades_count']
                ])

        print(f"  ✅ {filename} ({len(events)} events)")

print("\n" + "="*70)
print("📊 EVENT-LEVEL CSV EXPORT COMPLETE!")
print("="*70)
print("\nFiles created:")
print(f"1. all_events_detailed.csv - ALL {len(all_events)} events")
print(f"2. events_crossed_90_detailed.csv - {len(events_crossed_90)} events that crossed 90%")
print("3. events_<category>_90crossing.csv - Per-category breakdown files")
print("="*70)
