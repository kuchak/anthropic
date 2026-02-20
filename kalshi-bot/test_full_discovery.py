#!/usr/bin/env python3
"""Test full 100-page series discovery"""
import logging
import sys
import time
from series_discovery import SeriesDiscovery

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    stream=sys.stdout
)

print("Testing FULL 100-page discovery...")
print("="*60)

api_base = "https://api.elections.kalshi.com"
discovery = SeriesDiscovery(api_base_url=api_base)

start_time = time.time()
try:
    result = discovery.discover_series(max_pages=100)
    elapsed = time.time() - start_time

    print(f"\n✅ SUCCESS in {elapsed:.1f}s!")
    print(f"Found {len(result)} categories")
    total_series = sum(len(series_set) for series_set in result.values())
    print(f"Total unique series: {total_series}")
    print(f"Average: {elapsed/100:.2f}s per page")

    # Show categories and series counts
    for category, series_set in sorted(result.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"  {category}: {len(series_set)} series")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ ERROR after {elapsed:.1f}s: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
