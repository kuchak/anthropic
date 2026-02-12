"""
Check what markets and categories are actually available
"""
import os
import yaml
from kalshi_client import KalshiClient
from collections import Counter

# Set credentials
os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = '/root/.kalshi/private_key.pem'

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

print("Fetching all open markets...")
markets = client.get_markets(status='open', limit=1000)

print(f"\nFound {len(markets)} open markets")

# Analyze categories
categories = [m.get('series_ticker', 'unknown') for m in markets]
category_counts = Counter(categories)

print(f"\n📊 Available Categories:")
for cat, count in category_counts.most_common(20):
    print(f"  {cat}: {count} markets")

# Analyze prices
print(f"\n💰 Price Analysis:")
for market in markets[:10]:
    ticker = market.get('ticker', 'N/A')
    title = market.get('title', 'N/A')[:60]
    yes_ask = market.get('yes_ask', 0) / 100 if market.get('yes_ask') else 0
    no_ask = market.get('no_ask', 0) / 100 if market.get('no_ask') else 0
    category = market.get('series_ticker', 'unknown')

    print(f"\n  Ticker: {ticker}")
    print(f"  Title: {title}")
    print(f"  Category: {category}")
    print(f"  YES: ${yes_ask:.2f} | NO: ${no_ask:.2f}")
