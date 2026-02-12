"""
End-to-End Integration Test
Tests the complete trading bot system
"""
import os
import sys
import yaml
from logger_setup import setup_logger

logger = setup_logger("test_integration")


def test_integration():
    """Test complete system integration"""

    print("=" * 80)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 80)

    # Set credentials
    os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
    os.environ['KALSHI_PRIVATE_KEY_PATH'] = '/root/.kalshi/private_key.pem'

    # Import main after setting env vars
    from main import TradingBot

    # Load config
    print("\n📋 Loading configuration...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print("✅ Config loaded")

    # Initialize bot in dry-run mode
    print("\n🤖 Initializing trading bot (dry-run mode)...")
    try:
        bot = TradingBot(config, dry_run=True)
        print("✅ Bot initialized successfully")
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Run one complete cycle
    print("\n🔄 Running one complete trading cycle...")
    try:
        bot.run_once()
        print("✅ Trading cycle completed")
    except Exception as e:
        print(f"❌ Trading cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify components
    print("\n✅ Component Verification:")

    # Scanner
    scanner_stats = bot.scanner.get_stats()
    print(f"   Scanner: {scanner_stats['watchlist_size']} markets on watchlist")

    # Executor
    executor_stats = bot.executor.get_stats()
    print(f"   Executor: {executor_stats['total_executions']} executions")

    # Tracker
    tracker_report = bot.tracker.get_performance_report()
    print(f"   Tracker: {tracker_report['active_positions']} active positions")

    # Print final summary
    print("\n📊 Final Bot Status:")
    bot.tracker.print_summary()

    # Validation checks
    print("=" * 80)
    print("✅ Integration Test Validation:")

    # Check bot is in dry-run mode
    assert bot.dry_run == True, "Bot not in dry-run mode!"
    print("   ✓ Bot is in dry-run mode (safe)")

    # Check all components initialized
    assert bot.client is not None, "Client not initialized!"
    assert bot.scanner is not None, "Scanner not initialized!"
    assert bot.scorer is not None, "Scorer not initialized!"
    assert bot.allocator is not None, "Allocator not initialized!"
    assert bot.executor is not None, "Executor not initialized!"
    assert bot.tracker is not None, "Tracker not initialized!"
    print("   ✓ All components initialized")

    # Check tracker balance
    assert bot.tracker.starting_balance > 0, "Tracker balance not set!"
    print(f"   ✓ Tracker balance initialized (${bot.tracker.starting_balance:.2f})")

    # Check no live trades in dry-run
    if executor_stats['total_executions'] > 0:
        assert executor_stats['live_count'] == 0, "Live trades in dry-run mode!"
        print("   ✓ No live trades (dry-run mode verified)")

    print("\n" + "=" * 80)
    print("✅ END-TO-END INTEGRATION TEST PASSED")
    print("=" * 80)
    print("\n🎉 All systems operational!")
    print("🚀 Bot is ready for deployment!")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_integration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
