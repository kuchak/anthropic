import requests

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
response = requests.get(f"{API_BASE}/markets", params={'limit': 1000, 'status': 'open'})
markets = response.json().get('markets', [])

print(f"Checking {len(markets)} open markets...\n")

with_volume = []
for m in markets:
    vol = float(m.get('volume_24h_fp', 0) or m.get('volume_24h', 0) or 0)
    if vol > 0:
        ticker = m['ticker']
        series = ticker.split('-')[0] if '-' in ticker else ticker
        with_volume.append((ticker, series, vol))

print(f"Markets with ANY volume > 0: {len(with_volume)}\n")

# Sort by volume
with_volume.sort(key=lambda x: x[2], reverse=True)

for ticker, series, vol in with_volume[:50]:
    print(f"[{series}] {ticker[:60]} - ${vol:.0f}")

