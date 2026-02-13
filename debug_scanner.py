"""
Debug scanner to see where markets are being filtered out
"""
import sys
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')

import yaml
from kalshi_client import KalshiClient
from datetime import datetime
from dateutil.parser import parse as parse_datetime

# Load config
with open('/home/user/anthropic/kalshi-bot/config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

print("=" * 100)
print("SCANNER DEBUG - MARKET FILTERING PIPELINE")
print("=" * 100)
print()

# Step 1: Get total open markets
print("Step 1: Fetching ALL open markets...")
all_markets = client.get_markets(status='open', limit=1000)
print(f"  Total open markets: {len(all_markets)}")
print()

# Step 2: Query by whitelisted series
print("Step 2: Querying whitelisted series tickers...")
whitelist = config.get('series_ticker_whitelist', [])
print(f"  Whitelist has {len(whitelist)} tickers")

whitelisted_markets = []
for series in whitelist[:10]:  # First 10 to avoid rate limiting
    markets = client.get_markets(category=series, status='open', limit=1000)
    whitelisted_markets.extend(markets)
    if markets:
        print(f"    {series}: {len(markets)} markets")

print(f"  Total whitelisted markets: {len(whitelisted_markets)}")
print()

# Step 3: Check prices
print("Step 3: Checking price ranges...")
in_price_range = []
for m in whitelisted_markets:
    yes_price = m.get('yes_ask', 0) / 100.0 if m.get('yes_ask') else 0.0
    no_price = m.get('no_ask', 0) / 100.0 if m.get('no_ask') else 0.0

    if (0.90 <= yes_price <= 0.93) or (0.90 <= no_price <= 0.93):
        in_price_range.append(m)

print(f"  Markets in 90-93¢ range: {len(in_price_range)}")
print()

# Step 4: Show examples
if in_price_range:
    print("Examples of markets in range:")
    for m in in_price_range[:5]:
        ticker = m.get('ticker')
        # Extract series ticker
        series = ticker.split('-')[0] if '-' in ticker else ticker
        yes_price = m.get('yes_ask', 0) / 100.0
        no_price = m.get('no_ask', 0) / 100.0
        print(f"  {ticker}")
        print(f"    Series: {series}")
        print(f"    YES: ${yes_price:.2f}, NO: ${no_price:.2f}")
        print(f"    Status: {m.get('status')}")
else:
    print("⚠️  No markets in 90-93¢ range!")
    print()
    print("Sample markets from whitelist:")
    for m in whitelisted_markets[:5]:
        ticker = m.get('ticker')
        series = ticker.split('-')[0] if '-' in ticker else ticker
        yes_price = m.get('yes_ask', 0) / 100.0
        no_price = m.get('no_ask', 0) / 100.0
        print(f"  {ticker}")
        print(f"    Series: {series}")
        print(f"    YES: ${yes_price:.2f}, NO: ${no_price:.2f}")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"Total open markets: {len(all_markets)}")
print(f"Whitelisted markets: {len(whitelisted_markets)}")
print(f"In 90-93¢ range: {len(in_price_range)}")
print()

if len(in_price_range) == 0:
    print("❌ ISSUE: No markets in price range!")
    print()
    print("Possible reasons:")
    print("  1. Markets are not in 90-93¢ range (check prices above)")
    print("  2. All whitelisted markets are settled or inactive")
    print("  3. It's off-hours (no active games/events)")
