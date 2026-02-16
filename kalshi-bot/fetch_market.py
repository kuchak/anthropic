import os, yaml, json
from kalshi_client import KalshiClient

os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = './kalshi_private_key.pem'

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = KalshiClient(config)

ticker = "KXNCAAMBGAME-26FEB15HALLBUT"
print(f"Fetching market: {ticker}\n")

# Get single market
market = client.get_market(ticker)

if market:
    print("=" * 120)
    print("FULL MARKET DATA:")
    print("=" * 120)
    print(json.dumps(market, indent=2, sort_keys=True))
    print("\n" + "=" * 120)
    
    # Check if it's in is_live feed
    print("\nChecking if market is in is_live=true feed...")
    live_markets = client.get_markets(is_live='true', limit=1000, max_total=5000)
    tickers = [m['ticker'] for m in live_markets]
    
    if ticker in tickers:
        print(f"✅ YES - Market IS in the 5,000 is_live markets")
    else:
        print(f"❌ NO - Market NOT in the 5,000 is_live markets")
    
    # Calculate prices
    yes_bid = market.get('yes_bid', 0) / 100.0 if market.get('yes_bid') else 0.0
    no_bid = market.get('no_bid', 0) / 100.0 if market.get('no_bid') else 0.0
    yes_ask = market.get('yes_ask', 0) / 100.0 if market.get('yes_ask') else 0.0
    no_ask = market.get('no_ask', 0) / 100.0 if market.get('no_ask') else 0.0
    
    yes_price = yes_bid if yes_bid > 0 else yes_ask
    no_price = no_bid if no_bid > 0 else no_ask
    
    if yes_price == 0:
        yes_price = market.get('last_price', 0) / 100.0 if market.get('last_price') else 0.0
    if no_price == 0:
        no_price = 1.0 - yes_price if yes_price > 0 else 0.0
    
    print(f"\nPrice Analysis:")
    print(f"  YES: bid={yes_bid:.2f}¢ ask={yes_ask:.2f}¢ → price={yes_price:.2f}¢")
    print(f"  NO:  bid={no_bid:.2f}¢ ask={no_ask:.2f}¢ → price={no_price:.2f}¢")
    print(f"  In 85-97¢ range? YES={0.85 <= yes_price <= 0.97}, NO={0.85 <= no_price <= 0.97}")
else:
    print("❌ Market not found")

