#!/usr/bin/env python3
"""Test the Scanner.full_scan() method directly"""
import yaml
import sys
import time
from logger_setup import setup_logger
from kalshi_client import KalshiClient
from scanner import Scanner

# Setup logging
setup_logger("main")
setup_logger("scanner")
setup_logger("series_discovery")

print("Loading config...")
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Temporarily reduce pages for faster testing
config['series_discovery_pages'] = 10

print("Initializing API client...")
client = KalshiClient(config)

print("Initializing scanner...")
scanner = Scanner(client, config)

print("\n" + "="*60)
print("Calling scanner.full_scan()...")
print("="*60)

start_time = time.time()
try:
    count = scanner.full_scan(existing_position_tickers=[])
    elapsed = time.time() - start_time

    print(f"\n✅ SUCCESS in {elapsed:.1f}s!")
    print(f"Watchlist: {count} markets")
    print(f"Hot series: {len(scanner.hot_series)}")
    for series in sorted(scanner.hot_series)[:10]:
        print(f"  - {series}")
    if len(scanner.hot_series) > 10:
        print(f"  ... and {len(scanner.hot_series) - 10} more")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ ERROR after {elapsed:.1f}s: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
