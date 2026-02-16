import requests

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

url = f"{API_BASE}/markets"
params = {
    'limit': 1000,
    'status': 'open',
    'is_live': 'true'
}

all_markets = []
cursor = None

# Paginate through ALL markets
for page in range(5):  # Max 5 pages = 5000 markets
    if page > 0:
        params['cursor'] = cursor
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        break
    
    data = response.json()
    markets = data.get('markets', [])
    all_markets.extend(markets)
    
    cursor = data.get('cursor')
    if not cursor or not markets:
        break
    print(f"Page {page+1}: {len(markets)} markets (total: {len(all_markets)})")

print(f"\n📊 Total markets with is_live=true: {len(all_markets)}\n")

# Filter for 80-100¢ AND volume > 0
filtered = []
for m in all_markets:
    ticker = m['ticker']
    
    # Get yes/no prices
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
    
    volume_24h = float(m.get('volume_24h_fp', 0) or m.get('volume_24h', 0) or 0)
    
    # Filter: 80-100¢ AND volume > 0
    if ((0.80 <= yes_price <= 1.00) or (0.80 <= no_price <= 1.00)) and volume_24h > 0:
        filtered.append({
            'ticker': ticker,
            'title': m['title'],
            'yes': yes_price,
            'no': no_price,
            'volume_24h': volume_24h
        })

print(f"🎯 Markets with 80-100¢ AND volume > 0: {len(filtered)}\n")
print("=" * 120)

# Sort by volume descending
filtered.sort(key=lambda x: x['volume_24h'], reverse=True)

for i, m in enumerate(filtered, 1):
    print(f"{i:2d}. {m['ticker']}")
    print(f"    YES: {m['yes']:.2f}¢  NO: {m['no']:.2f}¢  VOL: ${m['volume_24h']:.0f}")
    print(f"    {m['title'][:100]}")
    print()

