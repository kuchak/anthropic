"""
Test script for Tracker module
"""
import os
import yaml
from datetime import datetime
from logger_setup import setup_logger
from kalshi_client import KalshiClient
from tracker import Tracker
from executor import TradeExecution

logger = setup_logger("test_tracker")


def create_test_execution(
    ticker: str,
    side: str,
    num_contracts: int,
    entry_price: float,
    status: str = "success"
) -> TradeExecution:
    """Create a test execution"""
    return TradeExecution(
        ticker=ticker,
        side=side,
        num_contracts=num_contracts,
        entry_price=entry_price,
        total_cost=num_contracts * entry_price,
        timestamp=datetime.utcnow(),
        execution_type="dry-run",
        order_id=None,
        status=status,
        error_message=None
    )


def test_tracker():
    """Test tracker functionality"""

    print("=" * 80)
    print("TRACKER MODULE TEST")
    print("=" * 80)

    # Set credentials
    os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
    os.environ['KALSHI_PRIVATE_KEY_PATH'] = '/root/.kalshi/private_key.pem'

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize client
    print("\n📡 Initializing API client...")
    client = KalshiClient(config)
    print("✅ API client ready")

    # Initialize tracker
    print("\n📊 Initializing tracker in DRY-RUN mode...")
    tracker = Tracker(client, dry_run=True)
    print("✅ Tracker initialized")

    # Initialize balance
    starting_balance = 1000.0
    print(f"\n💰 Initializing balance: ${starting_balance:.2f}")
    tracker.initialize_balance(starting_balance)
    print("✅ Balance initialized")

    # Create test executions
    print("\n📋 Creating test executions...")
    executions = [
        create_test_execution("TEST-WIN-1", "YES", 100, 0.87),
        create_test_execution("TEST-WIN-2", "NO", 50, 0.92),
        create_test_execution("TEST-LOSE-1", "YES", 75, 0.89),
        create_test_execution("TEST-FAIL-1", "YES", 25, 0.90, status="failed"),  # Should be skipped
    ]
    print(f"   Created {len(executions)} test executions")

    # Add executions
    print("\n➕ Adding executions to portfolio...")
    tracker.add_executions(executions)
    print("✅ Executions added")

    # Check active positions
    print(f"\n📊 Active Positions: {len(tracker.positions)}")
    for ticker, position in tracker.positions.items():
        print(f"\n   {ticker}:")
        print(f"      Side: {position.side}")
        print(f"      Contracts: {position.num_contracts}")
        print(f"      Entry Price: ${position.entry_price:.2f}")
        print(f"      Total Cost: ${position.total_cost:.2f}")

    # Test portfolio metrics
    print("\n📊 Portfolio Metrics:")
    print(f"   Total Exposure: ${tracker.get_total_exposure():.2f}")
    print(f"   Unrealized P&L: ${tracker.get_unrealized_pnl():.2f}")
    print(f"   Realized P&L: ${tracker.get_realized_pnl():.2f}")
    print(f"   Total P&L: ${tracker.get_total_pnl():.2f}")
    print(f"   Portfolio Value: ${tracker.get_portfolio_value():.2f}")

    # Simulate adding to existing position
    print("\n➕ Testing position averaging (add to TEST-WIN-1)...")
    additional_execution = create_test_execution("TEST-WIN-1", "YES", 50, 0.85)
    tracker.add_executions([additional_execution])

    updated_position = tracker.positions["TEST-WIN-1"]
    print(f"✅ Position updated:")
    print(f"   Contracts: {updated_position.num_contracts} (was 100)")
    print(f"   Avg Price: ${updated_position.entry_price:.2f}")
    print(f"   Total Cost: ${updated_position.total_cost:.2f}")

    # Test performance report
    print("\n📊 Generating performance report...")
    report = tracker.get_performance_report()
    print("✅ Performance Report:")
    print(f"   Starting Balance: ${report['starting_balance']:.2f}")
    print(f"   Current Balance: ${report['current_balance']:.2f}")
    print(f"   Portfolio Value: ${report['portfolio_value']:.2f}")
    print(f"   Active Positions: {report['active_positions']}")
    print(f"   Settled Positions: {report['settled_positions']}")
    print(f"   Total Exposure: ${report['total_exposure']:.2f}")
    print(f"   Realized P&L: ${report['realized_pnl']:+.2f}")
    print(f"   Unrealized P&L: ${report['unrealized_pnl']:+.2f}")
    print(f"   Total P&L: ${report['total_pnl']:+.2f}")
    print(f"   Total Return: {report['total_return_pct']:+.2f}%")
    print(f"   Win Rate: {report['win_rate']:.1f}%")

    # Print summary
    print("\n📊 Full Portfolio Summary:")
    tracker.print_summary()

    # Validation checks
    print("=" * 80)
    print("✅ Validation Checks:")

    # Check that failed execution was skipped
    assert "TEST-FAIL-1" not in tracker.positions, "Failed execution was added!"
    print("   ✓ Failed executions correctly skipped")

    # Check position count
    expected_positions = 3  # TEST-WIN-1, TEST-WIN-2, TEST-LOSE-1
    assert len(tracker.positions) == expected_positions, f"Expected {expected_positions} positions!"
    print(f"   ✓ Correct position count ({expected_positions})")

    # Check averaged position
    assert tracker.positions["TEST-WIN-1"].num_contracts == 150, "Position averaging failed!"
    print("   ✓ Position averaging working correctly")

    # Check total exposure
    total_cost = sum(p.total_cost for p in tracker.positions.values())
    assert abs(tracker.get_total_exposure() - total_cost) < 0.01, "Total exposure mismatch!"
    print(f"   ✓ Total exposure correct (${total_cost:.2f})")

    # Check no settled positions yet
    assert len(tracker.settled_positions) == 0, "Unexpected settled positions!"
    print("   ✓ No settlements yet (as expected)")

    # Check balance unchanged (no settlements)
    assert tracker.current_balance == starting_balance, "Balance changed without settlements!"
    print(f"   ✓ Balance unchanged (${tracker.current_balance:.2f})")

    print("\n" + "=" * 80)
    print("✅ TRACKER MODULE TEST PASSED")
    print("=" * 80)
    print("\n🚀 Ready to build main orchestration loop!")
    print()

    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_tracker()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
