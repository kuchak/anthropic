import os, yaml
from kalshi_client import KalshiClient

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)
markets = client.get_markets(is_live='true', limit=1000, max_total=5000)

print(f"Total markets: {len(markets)}\n")

# Apply the 3 filters
real_markets = []
for m in markets:
    ticker = m['ticker']
    
    # Filter 1: Skip MULTIGAME
    if 'MULTIGAME' in ticker:
        continue
    
    # Filter 2: Check price 85-97¢
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
    
    # Check if either side is 85-97¢
    if (0.85 <= yes_price <= 0.97) or (0.85 <= no_price <= 0.97):
        real_markets.append({
            'ticker': ticker,
            'series': ticker.split('-')[0],
            'title': m['title'][:100],
            'yes_price': yes_price,
            'no_price': no_price,
            'yes_bid': yes_bid,
            'yes_ask': yes_ask,
            'no_bid': no_bid,
            'no_ask': no_ask,
            'status': m.get('status')
        })

print(f"✅ Markets passing all 3 filters: {len(real_markets)}\n")

for i, m in enumerate(real_markets, 1):
    print(f"{i}. [{m['series']}] {m['ticker']}")
    print(f"   YES: bid={m['yes_bid']:.2f}¢ ask={m['yes_ask']:.2f}¢ → price={m['yes_price']:.2f}¢")
    print(f"   NO:  bid={m['no_bid']:.2f}¢ ask={m['no_ask']:.2f}¢ → price={m['no_price']:.2f}¢")
    print(f"   {m['title']}")
    print(f"   Status: {m['status']}")
    print()

