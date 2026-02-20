#!/usr/bin/env python3
"""Quick test of series discovery to see what's happening"""
import logging
import sys
from series_discovery import SeriesDiscovery

# Configure logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    stream=sys.stdout
)

print("Starting series discovery test...")
print("="*60)

api_base = "https://api.elections.kalshi.com"
discovery = SeriesDiscovery(api_base_url=api_base)

print(f"Testing with max_pages=2 first...")
try:
    result = discovery.discover_series(max_pages=2)
    print(f"\n✅ SUCCESS!")
    print(f"Found {len(result)} categories")
    total_series = sum(len(series_set) for series_set in result.values())
    print(f"Total series: {total_series}")

    for category, series_set in sorted(result.items()):
        print(f"  {category}: {len(series_set)} series")
        for series in sorted(series_set)[:3]:  # Show first 3
            print(f"    - {series}")
        if len(series_set) > 3:
            print(f"    ... and {len(series_set) - 3} more")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Test complete")
