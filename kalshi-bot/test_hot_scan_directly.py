#!/usr/bin/env python3
"""Test hot scan with a pre-populated hot list"""
import yaml
import time
from logger_setup import setup_logger
from kalshi_client import KalshiClient
from scanner import Scanner

# Setup logging
logger = setup_logger("main")
setup_logger("scanner")

print("Loading config...")
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("Initializing API client...")
client = KalshiClient(config)

print("Initializing scanner...")
scanner = Scanner(client, config)

# Manually populate hot list with whitelisted series
hot_series = set(config['series_ticker_whitelist'])
scanner.hot_series = hot_series

print(f"\n{'='*60}")
print(f"HOT SCAN TEST")
print(f"{'='*60}")
print(f"Hot list: {len(scanner.hot_series)} series")
for s in sorted(scanner.hot_series)[:10]:
    print(f"  - {s}")
if len(scanner.hot_series) > 10:
    print(f"  ... and {len(scanner.hot_series) - 10} more")

print(f"\n{'='*60}")
print("Running HOT SCAN...")
print(f"{'='*60}\n")

start_time = time.time()
try:
    count = scanner.hot_scan(existing_position_tickers=[])
    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ HOT SCAN COMPLETE in {elapsed:.1f} seconds!")
    print(f"{'='*60}")
    print(f"Watchlist: {count} markets found")
    print(f"Hot series count: {len(scanner.hot_series)}")
    print(f"Scan time: {elapsed:.2f}s")
    print(f"Time per series: {elapsed/len(hot_series):.2f}s")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ ERROR after {elapsed:.1f}s: {e}")
    import traceback
    traceback.print_exc()
