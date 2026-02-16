import os, yaml
from kalshi_client import KalshiClient

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)
markets = client.get_markets(status='open', is_live='true', limit=1000, max_total=5000)

print(f"📊 Total live markets: {len(markets)}\n")

# Count by price range
price_ranges = {
    '80-85¢': 0,
    '85-90¢': 0,
    '90-95¢': 0,
    '95-100¢': 0,
    'Other': 0
}

in_range_80_100 = []

for m in markets:
    yes_bid = m.get('yes_bid', 0) / 100.0 if m.get('yes_bid') else 0.0
    no_bid = m.get('no_bid', 0) / 100.0 if m.get('no_bid') else 0.0
    yes_ask = m.get('yes_ask', 0) / 100.0 if m.get('yes_ask') else 0.0
    no_ask = m.get('no_ask', 0) / 100.0 if m.get('no_ask') else 0.0
    
    yes_price = yes_bid if yes_bid > 0 else yes_ask
    no_price = no_bid if no_bid > 0 else no_ask
    
    if yes_price == 0:
        yes_price = m.get('last_price', 0) / 100.0 if m.get('last_price') else 0.0
    if no_price == 0:
        no_price = 1.0 - yes_price if yes_price > 0 else 0.0
    
    max_price = max(yes_price, no_price)
    
    if 0.80 <= max_price <= 0.85:
        price_ranges['80-85¢'] += 1
    elif 0.85 < max_price <= 0.90:
        price_ranges['85-90¢'] += 1
    elif 0.90 < max_price <= 0.95:
        price_ranges['90-95¢'] += 1
    elif 0.95 < max_price <= 1.00:
        price_ranges['95-100¢'] += 1
    else:
        price_ranges['Other'] += 1
    
    if 0.80 <= max_price <= 1.00:
        ticker = m['ticker']
        series = ticker.split('-')[0] if '-' in ticker else ticker
        vol = float(m.get('volume_24h_fp', 0) or 0)
        in_range_80_100.append((series, ticker, yes_price, no_price, vol))

print("Price Range Distribution:")
for range_name, count in price_ranges.items():
    print(f"  {range_name}: {count}")

print(f"\n🎯 Markets with 80-100¢ on either side: {len(in_range_80_100)}")
print(f"\nFirst 37 markets (matching your Kalshi LIVE page count):\n")
print("=" * 120)

for i, (series, ticker, yes, no, vol) in enumerate(in_range_80_100[:37], 1):
    print(f"{i:2d}. [{series}] {ticker[:70]}")
    print(f"    YES: {yes:.2f}¢  NO: {no:.2f}¢  VOL: ${vol:.0f}")
    print()

