"""
Convert existing JSON analysis files to detailed CSV format (tennis style)
"""

import json
import csv

print("="*70)
print("📊 CONVERTING JSON TO DETAILED CSV FORMAT")
print("="*70)

# 1. TENNIS MATCHES - Already have this format
print("\n1. Converting tennis_500_matches_analysis.json...")

with open('tennis_500_matches_analysis.json', 'r') as f:
    tennis_data = json.load(f)

matches = tennis_data['matches']
print(f"   Found {len(matches)} tennis matches")

#2. MULTI-SPORT ANALYSIS
print("\n2. Converting multi_sport_90_percent_analysis.json...")

with open('multi_sport_90_percent_analysis.json', 'r') as f:
    multisport_data = json.load(f)

# Extract all events from multi-sport
all_sport_events = []

for sport_data in multisport_data['sports']:
    sport_name = sport_data['sport']
    series_ticker = sport_data['series_ticker']

    if 'results' in sport_data:
        for result in sport_data['results']:
            event = {
                'category': 'Sports',
                'series_ticker': series_ticker,
                'series_title': sport_name,
                **result
            }
            all_sport_events.append(event)

print(f"   Found {len(all_sport_events)} sport events")

# 3. COMPREHENSIVE ANALYSIS - Need to fetch detailed data
#    For now, skip since it doesn't have event-level detail
print("\n3. Skipping comprehensive_kalshi_analysis.json (aggregated data only)")

# Export TENNIS to CSV
print("\n" + "="*70)
print("📝 CREATING CSV FILES")
print("="*70)

# TENNIS - All matches
print("\n1. Creating tennis_all_matches_detailed.csv...")
with open('tennis_all_matches_detailed.csv', 'w', newline='') as f:
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

    for match in matches:
        # Determine series info from ticker
        ticker = match['ticker']
        if 'KXATPMATCH' in ticker:
            series_ticker = 'KXATPMATCH'
            series_title = 'ATP Tennis Match'
        elif 'KXWTAMATCH' in ticker:
            series_ticker = 'KXWTAMATCH'
            series_title = 'WTA Tennis Match'
        else:
            series_ticker = 'UNKNOWN'
            series_title = 'Tennis Match'

        first_touch = match.get('first_touch', {}) or {}
        perm_cross = match.get('permanent_crossing', {}) or {}

        writer.writerow([
            'Sports',
            series_ticker,
            series_title,
            match['ticker'],
            match['title'],
            match['result'],
            match['settlement_value'],
            'YES' if match['crossed_90'] else 'NO',
            first_touch.get('timestamp', ''),
            first_touch.get('price', ''),
            perm_cross.get('timestamp', ''),
            perm_cross.get('price', ''),
            match['close_time'],
            match.get('betting_window_minutes', ''),
            match.get('betting_window_seconds', ''),
            'CORRECT' if match.get('prediction_correct') else ('WRONG' if match['crossed_90'] else ''),
            match.get('trades_count_a', 0) + match.get('trades_count_b', 0)
        ])

print(f"✅ Created tennis_all_matches_detailed.csv ({len(matches)} matches)")

# TENNIS - Only crossed 90%
crossed_tennis = [m for m in matches if m['crossed_90']]
print(f"\n2. Creating tennis_crossed_90_only.csv...")
with open('tennis_crossed_90_only.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Category',
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

    for match in crossed_tennis:
        ticker = match['ticker']
        if 'KXATPMATCH' in ticker:
            series_ticker = 'KXATPMATCH'
            series_title = 'ATP Tennis Match'
        elif 'KXWTAMATCH' in ticker:
            series_ticker = 'KXWTAMATCH'
            series_title = 'WTA Tennis Match'
        else:
            series_ticker = 'UNKNOWN'
            series_title = 'Tennis Match'

        first_touch = match.get('first_touch', {}) or {}
        perm_cross = match.get('permanent_crossing', {}) or {}

        writer.writerow([
            'Sports',
            series_ticker,
            series_title,
            match['ticker'],
            match['title'],
            match['result'],
            match['settlement_value'],
            first_touch.get('timestamp', ''),
            first_touch.get('price', ''),
            perm_cross.get('timestamp', ''),
            perm_cross.get('price', ''),
            match['close_time'],
            match['betting_window_minutes'],
            match['betting_window_seconds'],
            'CORRECT' if match.get('prediction_correct') else 'WRONG',
            match.get('trades_count_a', 0) + match.get('trades_count_b', 0)
        ])

print(f"✅ Created tennis_crossed_90_only.csv ({len(crossed_tennis)} matches)")

# MULTI-SPORT - All events
if all_sport_events:
    print(f"\n3. Creating multisport_all_events_detailed.csv...")
    with open('multisport_all_events_detailed.csv', 'w', newline='') as f:
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

        for event in all_sport_events:
            first_touch = event.get('first_touch', {}) or {}
            perm_cross = event.get('permanent_crossing', {}) or {}
            crossed_90 = event.get('crossed_90', first_touch != {})

            writer.writerow([
                event.get('category', ''),
                event.get('series_ticker', ''),
                event.get('series_title', ''),
                event.get('ticker', ''),
                event.get('title', ''),
                event.get('result', ''),
                event.get('settlement_value', ''),
                'YES' if crossed_90 else 'NO',
                first_touch.get('timestamp', ''),
                first_touch.get('price', ''),
                perm_cross.get('timestamp', ''),
                perm_cross.get('price', ''),
                event.get('close_time', ''),
                event.get('betting_window_minutes', ''),
                event.get('betting_window_seconds', ''),
                'CORRECT' if event.get('prediction_correct') else ('WRONG' if crossed_90 else ''),
                event.get('trades_count', '')
            ])

    print(f"✅ Created multisport_all_events_detailed.csv ({len(all_sport_events)} events)")

    # MULTI-SPORT - Only crossed 90%
    crossed_sport = [e for e in all_sport_events if e.get('crossed_90', e.get('first_touch', {}) != {})]
    print(f"\n4. Creating multisport_crossed_90_only.csv...")
    with open('multisport_crossed_90_only.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Category',
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

        for event in crossed_sport:
            first_touch = event.get('first_touch', {}) or {}
            perm_cross = event.get('permanent_crossing', {}) or {}

            writer.writerow([
                event.get('category', ''),
                event.get('series_ticker', ''),
                event.get('series_title', ''),
                event.get('ticker', ''),
                event.get('title', ''),
                event.get('result', ''),
                event.get('settlement_value', ''),
                first_touch.get('timestamp', ''),
                first_touch.get('price', ''),
                perm_cross.get('timestamp', ''),
                perm_cross.get('price', ''),
                event.get('close_time', ''),
                event.get('betting_window_minutes', ''),
                event.get('betting_window_seconds', ''),
                'CORRECT' if event.get('prediction_correct') else 'WRONG',
                event.get('trades_count', '')
            ])

    print(f"✅ Created multisport_crossed_90_only.csv ({len(crossed_sport)} events)")

print("\n" + "="*70)
print("✅ CSV CONVERSION COMPLETE!")
print("="*70)
print("\nCreated files:")
print("1. tennis_all_matches_detailed.csv - All tennis matches")
print("2. tennis_crossed_90_only.csv - Tennis matches that crossed 90%")
if all_sport_events:
    print("3. multisport_all_events_detailed.csv - All sport events")
    print("4. multisport_crossed_90_only.csv - Sport events that crossed 90%")
print("="*70)
