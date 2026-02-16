import os
from kalshi_client import KalshiClient
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Set env vars
os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

# Create client
client = KalshiClient(config)

# Get markets with is_live=true (same as bot)
markets = client.get_markets(
    status='open',
    is_live='true',
    limit=1000,
    max_total=5000
)

print(f"📊 Total markets with is_live=true: {len(markets)}\n")

# Find markets with volume > 0 AND 80-100¢
with_volume = []
for m in markets:
    vol = float(m.get('volume_24h_fp', 0) or m.get('volume_24h', 0) or 0)
    
    if vol > 0:
        ticker = m['ticker']
        series = ticker.split('-')[0] if '-' in ticker else ticker
        
        # Get prices
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
        
        # Check if 80-100¢ on either side
        if (0.80 <= yes_price <= 1.00) or (0.80 <= no_price <= 1.00):
            with_volume.append({
                'ticker': ticker,
                'series': series,
                'title': m['title'],
                'yes': yes_price,
                'no': no_price,
                'volume': vol
            })

print(f"🎯 Markets with volume > 0 AND 80-100¢: {len(with_volume)}\n")
print("=" * 120)

# Sort by volume
with_volume.sort(key=lambda x: x['volume'], reverse=True)

for i, m in enumerate(with_volume, 1):
    print(f"{i:2d}. [{m['series']}] {m['ticker']}")
    print(f"    YES: {m['yes']:.2f}¢  NO: {m['no']:.2f}¢  VOL: ${m['volume']:.2f}")
    print(f"    {m['title'][:100]}")
    print()

