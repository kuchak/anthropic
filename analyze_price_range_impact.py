"""
Analyze impact of expanding price range from 90-93¢ to 85-97¢
Shows how many additional markets would pass filters
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

print("=" * 120)
print("PRICE RANGE EXPANSION IMPACT ANALYSIS")
print("=" * 120)
print()

# Get all open markets
print("Fetching all open markets from Kalshi...")
all_markets = client.get_markets(status='open', limit=1000)
print(f"Retrieved {len(all_markets)} markets")
print()

now = datetime.now(timezone.utc)

# Categorize markets by price range
current_range = []  # 90-93¢
expanded_low = []   # 85-89¢
expanded_high = []  # 94-97¢
outside_all = []    # Everything else

for market in all_markets:
    ticker = market.get('ticker', '')

    # Get prices
    yes_ask = market.get('yes_ask', 0) / 100.0 if market.get('yes_ask') else 0.0
    no_ask = market.get('no_ask', 0) / 100.0 if market.get('no_ask') else 0.0

    if yes_ask == 0.0:
        yes_ask = market.get('last_price', 0) / 100.0 if market.get('last_price') else 0.0
    if no_ask == 0.0:
        no_ask = 1.0 - yes_ask if yes_ask > 0 else 0.0

    # Check which price ranges apply
    yes_in_current = 0.90 <= yes_ask <= 0.93
    no_in_current = 0.90 <= no_ask <= 0.93

    yes_in_expanded = 0.85 <= yes_ask <= 0.97
    no_in_expanded = 0.85 <= no_ask <= 0.97

    yes_in_low = 0.85 <= yes_ask <= 0.89
    no_in_low = 0.85 <= no_ask <= 0.89

    yes_in_high = 0.94 <= yes_ask <= 0.97
    no_in_high = 0.94 <= no_ask <= 0.97

    # Get expiration time
    exp_time_str = market.get('expected_expiration_time')
    if exp_time_str:
        try:
            exp_time = parse_datetime(exp_time_str)
            hours_until = (exp_time - now).total_seconds() / 3600
            within_4h = -1 <= hours_until <= 4
        except:
            within_4h = False
    else:
        within_4h = False

    # Get volume
    volume_24h = market.get('volume_24h', 0)
    has_volume = volume_24h > 0

    # Categorize
    market_info = {
        'ticker': ticker,
        'title': market.get('title', ''),
        'yes_price': yes_ask,
        'no_price': no_ask,
        'volume_24h': volume_24h,
        'hours_until': hours_until if exp_time_str else None,
        'within_4h': within_4h,
        'has_volume': has_volume
    }

    if yes_in_current or no_in_current:
        current_range.append(market_info)
    elif yes_in_low or no_in_low:
        expanded_low.append(market_info)
    elif yes_in_high or no_in_high:
        expanded_high.append(market_info)
    else:
        outside_all.append(market_info)

print("=" * 120)
print("PRICE RANGE BREAKDOWN")
print("=" * 120)
print()

print(f"Current range (90-93¢):")
print(f"  Total: {len(current_range)} markets")
within_4h_current = [m for m in current_range if m['within_4h'] and m['has_volume']]
print(f"  Within 4h + volume > 0: {len(within_4h_current)} markets")
print()

print(f"Expanded LOW range (85-89¢):")
print(f"  Total: {len(expanded_low)} markets")
within_4h_low = [m for m in expanded_low if m['within_4h'] and m['has_volume']]
print(f"  Within 4h + volume > 0: {len(within_4h_low)} markets")
print()

print(f"Expanded HIGH range (94-97¢):")
print(f"  Total: {len(expanded_high)} markets")
within_4h_high = [m for m in expanded_high if m['within_4h'] and m['has_volume']]
print(f"  Within 4h + volume > 0: {len(within_4h_high)} markets")
print()

print(f"Outside all ranges:")
print(f"  Total: {len(outside_all)} markets")
print()

# Combined expanded range
total_expanded = len(current_range) + len(expanded_low) + len(expanded_high)
total_expanded_passing = len(within_4h_current) + len(within_4h_low) + len(within_4h_high)

print("=" * 120)
print("IMPACT SUMMARY")
print("=" * 120)
print()

print(f"Current filters (90-93¢):")
print(f"  Markets in price range: {len(current_range)}")
print(f"  Markets passing ALL filters: {len(within_4h_current)}")
print()

print(f"After expansion (85-97¢):")
print(f"  Markets in price range: {total_expanded} (+{total_expanded - len(current_range)})")
print(f"  Markets passing ALL filters: {total_expanded_passing} (+{total_expanded_passing - len(within_4h_current)})")
print()

increase_pct = ((total_expanded - len(current_range)) / len(current_range) * 100) if len(current_range) > 0 else 0
print(f"Increase in opportunities: +{total_expanded - len(current_range)} markets ({increase_pct:.0f}% increase)")
print()

# Show examples of what we'd catch
if within_4h_low:
    print("=" * 120)
    print("EXAMPLES: Markets we'd catch at 85-89¢ (within 4h)")
    print("=" * 120)
    print()
    for market in within_4h_low[:5]:
        print(f"{market['ticker']}")
        print(f"  {market['title']}")
        print(f"  YES: ${market['yes_price']:.2f}, NO: ${market['no_price']:.2f}")
        print(f"  Hours until event: {market['hours_until']:.1f}h")
        print(f"  Volume 24h: ${market['volume_24h']:,.0f}")
        print()

if within_4h_high:
    print("=" * 120)
    print("EXAMPLES: Markets we'd catch at 94-97¢ (within 4h)")
    print("=" * 120)
    print()
    for market in within_4h_high[:5]:
        print(f"{market['ticker']}")
        print(f"  {market['title']}")
        print(f"  YES: ${market['yes_price']:.2f}, NO: ${market['no_price']:.2f}")
        print(f"  Hours until event: {market['hours_until']:.1f}h")
        print(f"  Volume 24h: ${market['volume_24h']:,.0f}")
        print()
