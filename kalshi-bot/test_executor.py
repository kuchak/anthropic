"""
Test script for Executor module
"""
import os
import yaml
from datetime import datetime, timedelta
from logger_setup import setup_logger
from models import Market
from scorer import ScoredOpportunity
from allocator import PositionAllocation
from kalshi_client import KalshiClient
from executor import Executor

logger = setup_logger("test_executor")


def create_test_allocation(ticker: str, entry_price: float, num_contracts: int) -> PositionAllocation:
    """Create a test allocation"""
    market = Market(
        ticker=ticker,
        title=f"Test market {ticker}",
        category="test",
        settlement_time=datetime.utcnow() + timedelta(hours=2),
        status="open",
        best_yes_price=entry_price,
        best_no_price=1.0 - entry_price,
        best_yes_size=100,
        best_no_size=100
    )

    opportunity = ScoredOpportunity(
        market=market,
        side="YES",
        entry_price=entry_price,
        win_probability=0.90,
        expected_profit=0.10,
        expected_roi=10.0,
        rank_score=10.0,
        time_to_settlement_hours=2.0
    )

    return PositionAllocation(
        opportunity=opportunity,
        kelly_fraction=0.15,
        adjusted_fraction=0.0375,
        position_size_dollars=num_contracts * entry_price,
        num_contracts=num_contracts,
        reasoning="Test allocation"
    )


def test_executor():
    """Test executor functionality"""

    print("=" * 80)
    print("EXECUTOR MODULE TEST")
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

    # Initialize executor in DRY-RUN mode
    print("\n🎬 Initializing executor in DRY-RUN mode...")
    executor = Executor(client, config, dry_run=True)
    print("✅ Executor initialized (dry-run mode - safe)")

    # Create test allocations
    print("\n📊 Creating test allocations...")
    allocations = [
        create_test_allocation("TEST-1", 0.87, 100),
        create_test_allocation("TEST-2", 0.92, 50),
        create_test_allocation("TEST-3", 0.89, 75),
    ]
    print(f"   Created {len(allocations)} test allocations")

    # Test dry-run execution
    print("\n🧪 Testing DRY-RUN execution...")
    executions = executor.execute_allocations(allocations)
    print(f"✅ Executed {len(executions)} positions")

    # Display executions
    if executions:
        print("\n📋 Execution Results:")
        for i, exec in enumerate(executions, 1):
            print(f"\n   {i}. {exec.ticker}")
            print(f"      Side: {exec.side}")
            print(f"      Contracts: {exec.num_contracts}")
            print(f"      Entry Price: ${exec.entry_price:.2f}")
            print(f"      Total Cost: ${exec.total_cost:.2f}")
            print(f"      Type: {exec.execution_type}")
            print(f"      Status: {exec.status}")
            if exec.error_message:
                print(f"      Error: {exec.error_message}")

        # Get stats
        print("\n📊 Execution Statistics:")
        stats = executor.get_stats()
        print(f"   Total executions: {stats['total_executions']}")
        print(f"   Successful: {stats['successful']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Total contracts: {stats['total_contracts']}")
        print(f"   Total cost: ${stats['total_cost']:.2f}")
        print(f"   Dry-run: {stats['dry_run_count']}")
        print(f"   Live: {stats['live_count']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")

    # Test execution history
    print("\n📜 Testing execution history...")
    history = executor.get_execution_history()
    print(f"✅ Retrieved {len(history)} executions from history")

    # Test mode switching (but stay in dry-run)
    print("\n🔄 Testing mode switching...")
    print("   Current mode: dry-run")
    executor.set_mode(dry_run=True)  # Should log "Already in dry-run mode"
    print("   ✅ Mode switch test complete (stayed in dry-run for safety)")

    # Validation checks
    print("\n✅ Validation Checks:")

    # Check all executions are dry-run
    assert all(e.execution_type == "dry-run" for e in executions), "Found live execution in dry-run mode!"
    print("   ✓ All executions are dry-run type")

    # Check all executions succeeded (they should in dry-run)
    assert all(e.status == "success" for e in executions), "Dry-run execution failed!"
    print("   ✓ All dry-run executions succeeded")

    # Check no order IDs (dry-run doesn't place real orders)
    assert all(e.order_id is None for e in executions), "Dry-run has order ID!"
    print("   ✓ No order IDs in dry-run mode")

    # Check execution history matches
    assert len(executor.get_execution_history()) == len(executions), "History mismatch!"
    print("   ✓ Execution history correctly tracked")

    # Check total cost calculation
    expected_total = sum(a.position_size_dollars for a in allocations)
    actual_total = sum(e.total_cost for e in executions if e.status == "success")
    assert abs(expected_total - actual_total) < 0.01, "Total cost mismatch!"
    print(f"   ✓ Total cost correct (${actual_total:.2f})")

    print("\n" + "=" * 80)
    print("✅ EXECUTOR MODULE TEST PASSED")
    print("=" * 80)
    print("\n🚀 Ready to build tracker module!")
    print()

    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_executor()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
