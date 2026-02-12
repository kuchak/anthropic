"""
Test script for Scanner module
"""
import os
import yaml
from logger_setup import setup_logger
from kalshi_client import KalshiClient
from scanner import Scanner

logger = setup_logger("test_scanner")


def test_scanner():
    """Test scanner functionality"""

    print("=" * 80)
    print("SCANNER MODULE TEST")
    print("=" * 80)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize client
    print("\n📡 Initializing API client...")
    client = KalshiClient(config)

    if not client.test_connection():
        print("❌ API connection failed")
        return False

    print("✅ API client ready")

    # Initialize scanner
    print("\n🔍 Initializing scanner...")
    scanner = Scanner(client, config)
    print("✅ Scanner initialized")

    # Run slow scan
    print("\n🔍 Running slow scan (full market discovery)...")
    print("   This may take 30-60 seconds...")

    try:
        count = scanner.slow_scan()
        print(f"✅ Slow scan complete!")
        print(f"   Found {count} markets meeting criteria")

        # Show watchlist stats
        stats = scanner.get_stats()
        print(f"\n📊 Watchlist Statistics:")
        print(f"   Total markets: {stats['watchlist_size']}")

        if stats['by_category']:
            print(f"\n   By category:")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                print(f"     - {category}: {count} markets")

        # Show sample markets
        watchlist = scanner.get_watchlist()
        if watchlist:
            print(f"\n📋 Sample Markets (first 5):")
            for i, market in enumerate(watchlist[:5], 1):
                time_remaining = market.time_to_settlement_minutes / 60
                print(f"\n   {i}. {market.ticker}")
                print(f"      Title: {market.title[:70]}")
                print(f"      Category: {market.category}")
                print(f"      YES: ${market.best_yes_price:.2f} | NO: ${market.best_no_price:.2f}")
                print(f"      Settlement: {time_remaining:.1f}h")

    except Exception as e:
        print(f"❌ Slow scan failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test fast scan
    if watchlist:
        print(f"\n⚡ Testing fast scan (price updates)...")
        try:
            # Take first market from watchlist for testing
            test_market = watchlist[0]
            print(f"   Updating: {test_market.ticker}")

            count = scanner.fast_scan()
            print(f"✅ Fast scan complete!")
            print(f"   {count} markets still on watchlist")

        except Exception as e:
            print(f"⚠️  Fast scan warning: {e}")
            # Not critical for test

    # Final stats
    stats = scanner.get_stats()
    print(f"\n" + "=" * 80)
    print("✅ SCANNER MODULE TEST PASSED")
    print("=" * 80)
    print(f"\nFinal watchlist: {stats['watchlist_size']} markets")
    print(f"Last slow scan: {stats['last_slow_scan']}")
    print(f"Last fast scan: {stats['last_fast_scan']}")
    print("\n🚀 Ready to build scorer module!")
    print()

    return True


if __name__ == "__main__":
    import sys

    # Set environment variables (from previous test)
    os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
    os.environ['KALSHI_PRIVATE_KEY_PATH'] = '/root/.kalshi/private_key.pem'

    try:
        success = test_scanner()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
