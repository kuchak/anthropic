"""
Test script to validate Kalshi API authentication
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
    print("KALSHI API AUTHENTICATION TEST")
    print("=" * 80)

    # Check environment variables
    email = os.getenv('KALSHI_EMAIL')
    password = os.getenv('KALSHI_PASSWORD')

    if not email or not password:
        print("\n❌ ERROR: Environment variables not set")
        print("   Please set KALSHI_EMAIL and KALSHI_PASSWORD")
        print("\n   Example:")
        print("   export KALSHI_EMAIL='your_email@example.com'")
        print("   export KALSHI_PASSWORD='your_password'")
        return False

    print(f"\n✅ Environment variables found")
    print(f"   Email: {email}")
    print(f"   Password: {'*' * len(password)}")

    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f"\n✅ Config loaded")
        print(f"   API Base: {config['kalshi_api_base']}")
        print(f"   Rate Limit: {config['api_requests_per_second']} req/sec")
    except Exception as e:
        print(f"\n❌ Failed to load config: {e}")
        return False

    # Initialize client
    try:
        client = KalshiClient(config)
        print(f"\n✅ Client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        return False

    # Test authentication
    print("\n🔐 Testing authentication...")
    try:
        success = client.authenticate()
        if not success:
            print("❌ Authentication failed")
            return False

        print("✅ Authentication successful!")
        print(f"   Token: {client.token[:20]}..." if client.token else "   No token")
        print(f"   Token expiry: {client.token_expiry}")
    except Exception as e:
        print(f"❌ Authentication error: {e}")
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
        return False

    # Test parsing a market
    print("\n🔍 Testing market parsing...")
    if markets:
        try:
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
                print("⚠️  Market parsing returned None")
        except Exception as e:
            print(f"❌ Market parsing error: {e}")
            return False

    # Test balance (if available)
    print("\n💰 Testing balance retrieval...")
    try:
        balance = client.get_balance()
        if balance is not None:
            print(f"✅ Account balance: ${balance:.2f}")
        else:
            print("⚠️  Balance retrieval returned None (may not have access)")
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
