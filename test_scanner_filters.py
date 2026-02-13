"""
Test script to show detailed scanner filter breakdown
"""
import sys
import os
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')

from kalshi_client import KalshiClient
from scanner import Scanner
import yaml

# Load config
with open('/home/user/anthropic/kalshi-bot/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize client
client = KalshiClient(config)

# Initialize scanner
scanner = Scanner(client, config)

# Run slow scan
print("=" * 100)
print("RUNNING SLOW SCAN")
print("=" * 100)
print()

watchlist_count = scanner.slow_scan()

print()
print("=" * 100)
print(f"RESULT: {watchlist_count} markets on watchlist")
print("=" * 100)
print()

# Show markets
if watchlist_count > 0:
    print("Markets on watchlist:")
    for market in scanner.get_watchlist():
        print(f"  - {market.ticker}: {market.title}")
        print(f"    YES: ${market.best_yes_price:.2f}, NO: ${market.best_no_price:.2f}")
        print(f"    Volume 24h: ${market.volume_24h:.2f}")
        print(f"    Category (series): {market.category}")
        print()
