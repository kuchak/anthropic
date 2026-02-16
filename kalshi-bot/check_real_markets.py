import requests
from datetime import datetime, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Try WITHOUT is_live filter
response = requests.get(f"{API_BASE}/markets", params={
    'limit': 1000,
    'status': 'open'
})

markets = response.json().get('markets', [])
print(f"📊 Total open markets (no is_live filter): {len(markets)}\n")

# Find markets with volume > 0
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
    print(f"    YES: {m['yes']:.2f}¢  NO: {m['no']:.2f}¢  VOL: ${m['volume']:.0f}")
    print(f"    {m['title'][:100]}")
    print()

