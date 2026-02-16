import os, yaml
from kalshi_client import KalshiClient
from scanner import Scanner
from datetime import datetime

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)
markets = client.get_markets(status='open', is_live='true', limit=1000, max_total=5000)

print(f"📊 Total live markets: {len(markets)}\n")

# Categorize by series ticker and price range
by_series = {}
in_range_85_97 = []

for m in markets:
    ticker = m['ticker']
    series = ticker.split('-')[0] if '-' in ticker else ticker
    
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
    
    # Track all series
    if series not in by_series:
        by_series[series] = 0
    by_series[series] += 1
    
    # Find markets in 85-97¢ range (bot's target)
    if 0.85 <= max_price <= 0.97:
        vol = float(m.get('volume_24h_fp', 0) or 0)
        liquidity = m.get('liquidity', 0)
        open_int = float(m.get('open_interest_fp', 0) or 0)
        
        in_range_85_97.append({
            'ticker': ticker,
            'series': series,
            'title': m['title'][:80],
            'yes': yes_price,
            'no': no_price,
            'volume_24h': vol,
            'liquidity': liquidity,
            'open_interest': open_int,
            'created': m.get('created_time', '')
        })

print("SERIES BREAKDOWN:")
for series, count in sorted(by_series.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"  {series:50s}: {count:4d} markets")

print(f"\n🎯 Markets in 85-97¢ range (bot target): {len(in_range_85_97)}")
print(f"\nShowing first 50 markets (sorted by price, NO volume filter):\n")
print("=" * 140)

# Sort by price descending
in_range_85_97.sort(key=lambda x: max(x['yes'], x['no']), reverse=True)

for i, m in enumerate(in_range_85_97[:50], 1):
    max_p = max(m['yes'], m['no'])
    print(f"{i:2d}. [{m['series'][:30]:30s}] {max_p:.2f}¢  VOL:${m['volume_24h']:.0f}  LIQ:${m['liquidity']/100:.2f}  OI:{m['open_interest']:.0f}")
    print(f"    {m['ticker'][:100]}")
    print(f"    {m['title']}")
    print()

# Check for non-parlay markets
non_parlay = [m for m in in_range_85_97 if 'MULTIGAME' not in m['series']]
print(f"\n📌 NON-PARLAY markets in 85-97¢ range: {len(non_parlay)}")
if non_parlay:
    print("\nFirst 10 non-parlay markets:")
    for i, m in enumerate(non_parlay[:10], 1):
        print(f"{i}. [{m['series']}] {m['ticker']}")
        print(f"   {m['title']}")

