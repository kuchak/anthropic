"""
Diagnose tennis market filtering
Shows ALL tennis markets and why they pass/fail filters
"""
import sys
sys.path.insert(0, '/home/user/anthropic/kalshi-bot')

from kalshi_client import KalshiClient
from datetime import datetime, timezone
from dateutil.parser import parse as parse_datetime
import yaml

with open('/home/user/anthropic/kalshi-bot/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

# Get all tennis markets
tennis_series = ['KXATPMATCH', 'KXWTAMATCH', 'KXATPCHALLENGERMATCH', 'KXWTACHALLENGERMATCH', 'KXUNITEDCUPMATCH']

print("=" * 120)
print("ALL TENNIS MARKETS FROM KALSHI API")
print("=" * 120)
print()

now = datetime.now(timezone.utc)
all_tennis = []

for series in tennis_series:
    markets = client.get_markets(category=series, status='open', limit=1000)
    all_tennis.extend(markets)
    print(f"Found {len(markets)} markets in {series}")

print(f"\nTotal tennis markets: {len(all_tennis)}")
print()

# Analyze each market
print("=" * 120)
print("DETAILED FILTER ANALYSIS")
print("=" * 120)
print()

for market in all_tennis:
    ticker = market['ticker']
    title = market['title']

    # Get prices
    yes_ask = market.get('yes_ask', 0) / 100.0 if market.get('yes_ask') else 0.0
    no_ask = market.get('no_ask', 0) / 100.0 if market.get('no_ask') else 0.0

    if yes_ask == 0.0:
        yes_ask = market.get('last_price', 0) / 100.0 if market.get('last_price') else 0.0
    if no_ask == 0.0:
        no_ask = 1.0 - yes_ask if yes_ask > 0 else 0.0

    # Get volume
    volume_24h = market.get('volume_24h', 0)

    # Get expiration time
    exp_time_str = market.get('expected_expiration_time', 'N/A')
    if exp_time_str != 'N/A':
        exp_time = parse_datetime(exp_time_str)
        hours_until = (exp_time - now).total_seconds() / 3600
    else:
        exp_time = None
        hours_until = None

    # Check filters
    status = market.get('status', 'unknown')

    # Filter checks
    filters = {
        'status_ok': status in ['open', 'active'],
        'volume_ok': volume_24h > 0,
        'price_ok': (0.90 <= yes_ask <= 0.93) or (0.90 <= no_ask <= 0.93),
        'time_ok': hours_until is not None and (-1 <= hours_until <= 4) if hours_until is not None else False
    }

    passes = all(filters.values())

    print(f"Ticker: {ticker}")
    print(f"  Title: {title}")
    print(f"  YES: ${yes_ask:.2f}, NO: ${no_ask:.2f}")
    print(f"  Volume 24h: ${volume_24h:,.0f}")
    if exp_time:
        print(f"  Expected expiration: {exp_time} ({hours_until:.1f}h from now)")
    else:
        print(f"  Expected expiration: N/A")
    print(f"  Status: {status}")
    print(f"  Filter results:")
    print(f"    ✅ Status open/active: {filters['status_ok']}")
    print(f"    {'✅' if filters['volume_ok'] else '❌'} Volume > 0: {filters['volume_ok']}")
    print(f"    {'✅' if filters['price_ok'] else '❌'} Price 90-93¢: {filters['price_ok']}")
    print(f"    {'✅' if filters['time_ok'] else '❌'} Event within 4h: {filters['time_ok']}")
    print(f"  {'✅ PASSES ALL FILTERS' if passes else '❌ FILTERED OUT'}")
    print()

# Summary
passing = [m for m in all_tennis if (
    m.get('status') in ['open', 'active'] and
    m.get('volume_24h', 0) > 0 and
    (
        (0.90 <= (m.get('yes_ask', 0) / 100.0 if m.get('yes_ask') else (m.get('last_price', 0) / 100.0 if m.get('last_price') else 0.0)) <= 0.93) or
        (0.90 <= (m.get('no_ask', 0) / 100.0 if m.get('no_ask') else (1.0 - (m.get('last_price', 0) / 100.0 if m.get('last_price') else 0.0))) <= 0.93)
    ) and
    m.get('expected_expiration_time') and
    -1 <= (parse_datetime(m['expected_expiration_time']) - now).total_seconds() / 3600 <= 4
)]

print("=" * 120)
print("SUMMARY")
print("=" * 120)
print(f"Total tennis markets: {len(all_tennis)}")
print(f"Markets passing all filters: {len(passing)}")
print()
