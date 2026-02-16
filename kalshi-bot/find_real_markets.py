import os, yaml
from kalshi_client import KalshiClient
from datetime import datetime, timedelta

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

# Get markets WITHOUT is_live filter
print("Fetching markets WITHOUT is_live filter...\n")
markets = client.get_markets(status='open', limit=1000, max_total=3000)

print(f"📊 Total open markets: {len(markets)}\n")

# Find REAL (non-parlay) markets in 85-97¢ range
real_markets = []
for m in markets:
    ticker = m['ticker']
    series = ticker.split('-')[0] if '-' in ticker else ticker
    
    # Skip parlays
    if 'MULTIGAME' in series:
        continue
    
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
    
    if 0.85 <= max_price <= 0.97:
        vol = float(m.get('volume_24h_fp', 0) or 0)
        open_int = float(m.get('open_interest_fp', 0) or 0)
        
        real_markets.append({
            'ticker': ticker,
            'series': series,
            'title': m['title'][:100],
            'yes': yes_price,
            'no': no_price,
            'volume_24h': vol,
            'open_interest': open_int,
            'expected_exp': m.get('expected_expiration_time', ''),
            'status': m.get('status', '')
        })

print(f"🎯 REAL (non-parlay) markets in 85-97¢ range: {len(real_markets)}")

if real_markets:
    # Sort by open interest descending
    real_markets.sort(key=lambda x: x['open_interest'], reverse=True)
    
    print("\nTop 30 by open interest:\n")
    print("=" * 140)
    
    for i, m in enumerate(real_markets[:30], 1):
        max_p = max(m['yes'], m['no'])
        print(f"{i:2d}. [{m['series'][:25]:25s}] {max_p:.2f}¢  VOL:${m['volume_24h']:.0f}  OI:{m['open_interest']:.0f}")
        print(f"    {m['ticker']}")
        print(f"    {m['title']}")
        print(f"    Exp: {m['expected_exp']}")
        print()
else:
    print("\n❌ No real markets found in 85-97¢ range")

