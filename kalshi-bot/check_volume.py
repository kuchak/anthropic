import requests

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
response = requests.get(f"{API_BASE}/markets", params={'limit': 100, 'status': 'open', 'is_live': 'true'})
markets = response.json().get('markets', [])

print(f"Checking first {len(markets)} live markets for volume...\n")

volume_counts = {
    'volume_24h_fp': 0,
    'volume_24h': 0,
    'any_volume': 0
}

for m in markets[:20]:  # Check first 20
    vol_fp = m.get('volume_24h_fp')
    vol = m.get('volume_24h')
    
    print(f"{m['ticker'][:50]}")
    print(f"  volume_24h_fp: {vol_fp}")
    print(f"  volume_24h: {vol}")
    
    if vol_fp and float(vol_fp) > 0:
        volume_counts['volume_24h_fp'] += 1
    if vol and int(vol) > 0:
        volume_counts['volume_24h'] += 1
    if (vol_fp and float(vol_fp) > 0) or (vol and int(vol) > 0):
        volume_counts['any_volume'] += 1

print(f"\nSummary of first 20 markets:")
print(f"  Markets with volume_24h_fp > 0: {volume_counts['volume_24h_fp']}")
print(f"  Markets with volume_24h > 0: {volume_counts['volume_24h']}")
print(f"  Markets with ANY volume: {volume_counts['any_volume']}")

