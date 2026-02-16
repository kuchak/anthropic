import os, yaml, json
from kalshi_client import KalshiClient

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)
markets = client.get_markets(status='open', is_live='true', limit=1000, max_total=5000)

# Find markets in 90-95¢ range
in_range = []
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
    
    if 0.90 <= max_price <= 0.95:
        in_range.append(m)

print(f"Found {len(in_range)} markets in 90-95¢ range\n")

if in_range:
    print("=" * 120)
    print("RAW API RESPONSE FOR FIRST MARKET IN 90-95¢ RANGE:")
    print("=" * 120)
    print(json.dumps(in_range[0], indent=2, sort_keys=True))
    print("\n" + "=" * 120)
    print("ALL FIELD NAMES:")
    print("=" * 120)
    for key in sorted(in_range[0].keys()):
        value = in_range[0][key]
        print(f"  {key:40s} = {value}")

