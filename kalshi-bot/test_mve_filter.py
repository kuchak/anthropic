"""
Test script to verify mve_filter parameter works correctly
"""
import yaml
from kalshi_client import KalshiClient

print("=" * 80)
print("TESTING MVE_FILTER PARAMETER")
print("=" * 80)
print()

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize client
client = KalshiClient(config)

print("Testing mve_filter parameter...")
print()

# Test 1: Get markets WITHOUT mve_filter (old way)
print("Test 1: Fetching 100 markets WITHOUT mve_filter...")
markets_without_filter = client.get_markets(
    is_live='true',
    limit=100,
    max_total=100
)
print(f"  Retrieved: {len(markets_without_filter)} markets")

# Count MULTIGAME markets
multigame_count_without = sum(1 for m in markets_without_filter if 'MULTIGAME' in m.get('ticker', ''))
print(f"  MULTIGAME markets: {multigame_count_without} ({multigame_count_without/len(markets_without_filter)*100:.1f}%)")
print()

# Test 2: Get markets WITH mve_filter='exclude' (new way)
print("Test 2: Fetching 100 markets WITH mve_filter='exclude'...")
markets_with_filter = client.get_markets(
    is_live='true',
    mve_filter='exclude',
    limit=100,
    max_total=100
)
print(f"  Retrieved: {len(markets_with_filter)} markets")

# Count MULTIGAME markets
multigame_count_with = sum(1 for m in markets_with_filter if 'MULTIGAME' in m.get('ticker', ''))
print(f"  MULTIGAME markets: {multigame_count_with} ({multigame_count_with/len(markets_with_filter)*100:.1f}%)")
print()

# Test 3: Check for NCAA basketball markets
print("Test 3: Checking for NCAA basketball markets in filtered results...")
ncaa_bball = [m for m in markets_with_filter if 'KXNCAAMBGAME' in m.get('ticker', '')]
print(f"  Found {len(ncaa_bball)} NCAA basketball markets")
if ncaa_bball:
    for m in ncaa_bball[:5]:
        print(f"    - {m['ticker']}: {m.get('title', '')}")
print()

# Test 4: Show diversity of market types
print("Test 4: Market type diversity (series tickers)...")
series_counts = {}
for m in markets_with_filter:
    ticker = m.get('ticker', '')
    series = ticker.split('-')[0] if '-' in ticker else ticker
    series_counts[series] = series_counts.get(series, 0) + 1

print(f"  Found {len(series_counts)} different series tickers:")
for series, count in sorted(series_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"    {series}: {count}")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
if multigame_count_without > 0 and multigame_count_with == 0:
    print("✅ SUCCESS: mve_filter='exclude' correctly filters out MULTIGAME parlays")
else:
    print(f"⚠️  WARNING: Expected 0 MULTIGAME markets with filter, got {multigame_count_with}")

if len(ncaa_bball) > 0:
    print(f"✅ SUCCESS: Found {len(ncaa_bball)} NCAA basketball markets (previously 0)")
else:
    print("⚠️  No NCAA basketball markets found (may not be live right now)")

print()
