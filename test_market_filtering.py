"""
Test the exact market we know exists
"""
import sys
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')

import yaml
from kalshi_client import KalshiClient
from models import Market
from dateutil.parser import parse as parse_datetime

# Load config
with open('/home/user/anthropic/kalshi-bot/config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

# Get the specific market
print("Fetching KXSCOTTISHPREMGAME markets...")
markets = client.get_markets(category='KXSCOTTISHPREMGAME', status='open', limit=100)

print(f"Found {len(markets)} markets\n")

# Find the one in our price range
target_market = None
for m in markets:
    ticker = m.get('ticker')
    if 'KILCEL' in ticker:
        target_market = m
        break

if not target_market:
    print("❌ Market not found!")
    sys.exit(1)

print(f"Target market: {target_market['ticker']}")
print()

# Parse it
yes_price = target_market.get('yes_ask', 0) / 100.0
no_price = target_market.get('no_ask', 0) / 100.0
ticker = target_market['ticker']
series_ticker = ticker.split('-')[0]

print(f"Parsed data:")
print(f"  Ticker: {ticker}")
print(f"  Series: {series_ticker}")
print(f"  YES price: ${yes_price:.2f}")
print(f"  NO price: ${no_price:.2f}")
print(f"  Status: {target_market.get('status')}")
print(f"  Close time: {target_market.get('close_time')}")
print()

# Check filters
print("Checking filters:")
print()

# 1. Whitelist check
whitelist = config.get('series_ticker_whitelist', [])
in_whitelist = series_ticker in whitelist
print(f"1. Whitelist: {series_ticker} in whitelist? {in_whitelist}")
print()

# 2. Price check
min_price = config['min_contract_price']
max_price = config['max_contract_price']
yes_in_range = min_price <= yes_price <= max_price
no_in_range = min_price <= no_price <= max_price
price_ok = yes_in_range or no_in_range

print(f"2. Price check:")
print(f"   Price range: ${min_price:.2f} - ${max_price:.2f}")
print(f"   YES ${yes_price:.2f} in range? {yes_in_range}")
print(f"   NO ${no_price:.2f} in range? {no_in_range}")
print(f"   PASSES? {price_ok}")
print()

# 3. Settlement time check
from datetime import datetime, timezone
close_time = parse_datetime(target_market.get('close_time'))
now = datetime.now(timezone.utc)
minutes_to_settlement = (close_time - now).total_seconds() / 60

min_settlement_mins = config['min_time_to_settlement_minutes']
max_settlement_hours = config['max_time_to_settlement_hours']
max_settlement_mins = max_settlement_hours * 60

settlement_ok = min_settlement_mins <= minutes_to_settlement <= max_settlement_mins

print(f"3. Settlement time check:")
print(f"   Minutes to settlement: {minutes_to_settlement:.1f}")
print(f"   Min: {min_settlement_mins} min, Max: {max_settlement_mins} min")
print(f"   PASSES? {settlement_ok}")
print()

# 4. Status check
status_ok = target_market.get('status') in ['open', 'active']
print(f"4. Status check:")
print(f"   Status: {target_market.get('status')}")
print(f"   PASSES? {status_ok}")
print()

# Overall
print("=" * 80)
print("OVERALL RESULT:")
print(f"  Whitelist: {in_whitelist}")
print(f"  Price: {price_ok}")
print(f"  Settlement: {settlement_ok}")
print(f"  Status: {status_ok}")
print()
should_pass = in_whitelist and price_ok and settlement_ok and status_ok
print(f"  Should be on watchlist: {should_pass}")

if not should_pass:
    print()
    print("❌ FAILING CRITERIA:")
    if not in_whitelist:
        print("  - Not in whitelist")
    if not price_ok:
        print("  - Price not in range")
    if not settlement_ok:
        print(f"  - Settlement time ({minutes_to_settlement:.1f} min) not in range")
    if not status_ok:
        print("  - Status not 'open' or 'active'")
