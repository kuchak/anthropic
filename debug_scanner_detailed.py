"""
Run the actual scanner and see what happens
"""
import sys
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')

import yaml
from kalshi_client import KalshiClient
from scanner import Scanner

# Load config
with open('/home/user/anthropic/kalshi-bot/config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)
scanner = Scanner(client, config)

print("=" * 100)
print("RUNNING ACTUAL SCANNER")
print("=" * 100)
print()

# Run slow scan
print("Running slow scan...")
count = scanner.slow_scan()

print(f"\nWatchlist size: {count}")
print()

watchlist = scanner.get_watchlist()
if watchlist:
    print("Markets on watchlist:")
    for m in watchlist:
        print(f"  {m.ticker}")
        print(f"    Category: {m.category}")
        print(f"    YES: ${m.best_yes_price:.2f}, NO: ${m.best_no_price:.2f}")
        print(f"    Status: {m.status}")
        print()
else:
    print("❌ Watchlist is empty!")
    print()
    print("The scanner filtered out all markets.")
    print("Check the scanner logs above for filter breakdown.")
