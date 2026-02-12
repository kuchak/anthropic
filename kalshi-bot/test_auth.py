"""
Test script to validate Kalshi API authentication with API keys
Run this first to ensure API credentials and connection work
"""
import os
import sys
import yaml
from logger_setup import setup_logger
from kalshi_client import KalshiClient

# Setup logging
logger = setup_logger("test_auth")


def test_authentication():
    """Test API authentication and basic endpoints"""

    print("=" * 80)
    print("KALSHI API AUTHENTICATION TEST (API Keys)")
    print("=" * 80)

    # Check environment variables
    api_key_id = os.getenv('KALSHI_API_KEY_ID')
    private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

    if not api_key_id or not private_key_path:
        print("\n❌ ERROR: Environment variables not set")
        print("   Please set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH")
        print("\n   How to get API keys:")
        print("   1. Go to https://demo.kalshi.com/account/profile (for demo)")
        print("      Or https://kalshi.com/account/profile (for production)")
        print("   2. Click 'Create New API Key'")
        print("   3. Download the private key file")
        print("   4. Note your Key ID")
        print("\n   Then set environment variables:")
        print("   export KALSHI_API_KEY_ID='your_key_id_here'")
        print("   export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'")
        return False

    print(f"\n✅ Environment variables found")
    print(f"   API Key ID: {api_key_id}")
    print(f"   Private Key Path: {private_key_path}")

    # Check if private key file exists
    if not os.path.exists(private_key_path):
        print(f"\n❌ ERROR: Private key file not found at {private_key_path}")
        return False

    print(f"   ✅ Private key file exists")

    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f"\n✅ Config loaded")
        print(f"   API Base: {config['kalshi_api_base']}")
        print(f"   Rate Limit: {config['api_requests_per_second']} req/sec")

        # Show if using demo or production
        if 'demo' in config['kalshi_api_base']:
            print(f"   🧪 Using DEMO API (safe for testing)")
        else:
            print(f"   💰 Using PRODUCTION API (real money!)")
    except Exception as e:
        print(f"\n❌ Failed to load config: {e}")
        return False

    # Initialize client
    try:
        client = KalshiClient(config)
        print(f"\n✅ Client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test connection and authentication
    print("\n🔐 Testing API connection and authentication...")
    try:
        success = client.test_connection()
        if not success:
            print("❌ API connection test failed")
            return False

        print("✅ API authentication successful!")
    except Exception as e:
        print(f"❌ API connection error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test getting markets
    print("\n📊 Testing market data retrieval...")
    try:
        markets = client.get_markets(status='open', limit=5)
        print(f"✅ Retrieved {len(markets)} open markets")

        if markets:
            print("\n   Sample markets:")
            for market in markets[:3]:
                ticker = market.get('ticker', 'N/A')
                title = market.get('title', 'N/A')
                print(f"   - {ticker}: {title[:60]}")
    except Exception as e:
        print(f"❌ Failed to get markets: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test parsing a market
    print("\n🔍 Testing market parsing...")
    if markets:
        try:
            print("   Parsing first market (this may take a few seconds)...")
            market_obj = client.parse_market(markets[0])
            if market_obj:
                print(f"✅ Successfully parsed market")
                print(f"   Ticker: {market_obj.ticker}")
                print(f"   Title: {market_obj.title}")
                print(f"   Category: {market_obj.category}")
                print(f"   Best YES: ${market_obj.best_yes_price:.2f}")
                print(f"   Best NO: ${market_obj.best_no_price:.2f}")
                print(f"   Time to settlement: {market_obj.time_to_settlement_minutes:.1f} minutes")
            else:
                print("⚠️  Market parsing returned None (orderbook may be empty)")
        except Exception as e:
            print(f"⚠️  Market parsing error: {e}")
            # Not critical for auth test

    # Test balance (if available)
    print("\n💰 Testing balance retrieval...")
    try:
        balance = client.get_balance()
        if balance is not None:
            print(f"✅ Account balance: ${balance:.2f}")
        else:
            print("⚠️  Balance retrieval returned None")
    except Exception as e:
        print(f"⚠️  Balance check error: {e}")
        # Not critical, continue

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - API authentication and connection working!")
    print("=" * 80)
    print("\n🚀 Ready to build the next module (scanner.py)")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_authentication()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
