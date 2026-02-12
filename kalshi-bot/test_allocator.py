"""
Test script for Allocator module
"""
import yaml
from datetime import datetime, timedelta
from logger_setup import setup_logger
from models import Market
from scorer import Scorer, ScoredOpportunity
from allocator import Allocator

logger = setup_logger("test_allocator")


def create_test_opportunity(
    ticker: str,
    entry_price: float,
    win_probability: float,
    expected_roi: float,
    settlement_hours: float
) -> ScoredOpportunity:
    """Create a test opportunity"""
    market = Market(
        ticker=ticker,
        title=f"Test market {ticker}",
        category="test",
        settlement_time=datetime.utcnow() + timedelta(hours=settlement_hours),
        status="open",
        best_yes_price=entry_price,
        best_no_price=1.0 - entry_price,
        best_yes_size=100,
        best_no_size=100
    )

    expected_profit = expected_roi * entry_price / 100

    return ScoredOpportunity(
        market=market,
        side="YES",
        entry_price=entry_price,
        win_probability=win_probability,
        expected_profit=expected_profit,
        expected_roi=expected_roi,
        rank_score=expected_roi,  # Simplified
        time_to_settlement_hours=settlement_hours
    )


def test_allocator():
    """Test allocator functionality"""

    print("=" * 80)
    print("ALLOCATOR MODULE TEST")
    print("=" * 80)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Set test balance
    test_balance = 1000.0

    # Initialize allocator
    print(f"\n💰 Initializing allocator with ${test_balance:.2f} balance...")
    allocator = Allocator(config, test_balance)
    print("✅ Allocator initialized")
    print(f"   Kelly fraction: {allocator.kelly_fraction * 100:.0f}%")
    print(f"   Max position size: {allocator.max_position_size_pct * 100:.0f}% (${test_balance * allocator.max_position_size_pct:.2f})")
    print(f"   Max total exposure: {allocator.max_total_exposure_pct * 100:.0f}% (${test_balance * allocator.max_total_exposure_pct:.2f})")

    # Create test opportunities with varying characteristics
    print("\n📊 Creating test opportunities...")
    opportunities = [
        # High confidence, good price - should get large allocation
        create_test_opportunity("TEST-BEST-1", 0.87, 0.912, 10.0, 2.0),

        # Medium confidence, decent price
        create_test_opportunity("TEST-GOOD-1", 0.90, 0.894, 8.0, 3.0),

        # Lower confidence, okay price
        create_test_opportunity("TEST-OK-1", 0.92, 0.85, 5.0, 2.5),

        # Marginal opportunity - might be too small
        create_test_opportunity("TEST-MARGINAL-1", 0.95, 0.80, 2.0, 4.0),

        # Very small edge - probably gets filtered
        create_test_opportunity("TEST-TINY-1", 0.97, 0.75, 1.0, 1.0),
    ]

    print(f"   Created {len(opportunities)} test opportunities")

    # Test basic allocation
    print("\n💵 Testing position allocation...")
    allocations = allocator.allocate_positions(opportunities, current_exposure=0.0)
    print(f"✅ Allocated {len(allocations)} positions")

    # Display allocations
    if allocations:
        print("\n📋 Position Allocations:")
        for i, alloc in enumerate(allocations, 1):
            opp = alloc.opportunity
            print(f"\n   {i}. {opp.market.ticker}")
            print(f"      Entry Price: ${alloc.opportunity.entry_price:.2f}")
            print(f"      Win Probability: {opp.win_probability * 100:.1f}%")
            print(f"      Expected ROI: {opp.expected_roi:.2f}%")
            print(f"      Kelly Fraction: {alloc.kelly_fraction * 100:.2f}%")
            print(f"      Adjusted (25%): {alloc.adjusted_fraction * 100:.2f}%")
            print(f"      Position Size: ${alloc.position_size_dollars:.2f}")
            print(f"      Contracts: {alloc.num_contracts}")
            print(f"      Reasoning: {alloc.reasoning}")

        # Get stats
        print("\n📊 Allocation Statistics:")
        stats = allocator.get_stats(allocations)
        print(f"   Total positions: {stats['total_positions']}")
        print(f"   Total allocated: ${stats['total_allocated']:.2f}")
        print(f"   Total contracts: {stats['total_contracts']}")
        print(f"   Avg position size: ${stats['avg_position_size']:.2f}")
        print(f"   Largest position: ${stats['largest_position']:.2f}")
        print(f"   Smallest position: ${stats['smallest_position']:.2f}")
        print(f"   % of balance allocated: {stats['pct_of_balance_allocated']:.1f}%")

    # Test with existing exposure
    print("\n🔒 Testing with existing exposure...")
    existing_exposure = 400.0
    print(f"   Simulating ${existing_exposure:.2f} already allocated")
    allocations_with_exposure = allocator.allocate_positions(opportunities, current_exposure=existing_exposure)
    print(f"✅ Allocated {len(allocations_with_exposure)} positions with existing exposure")
    total_new = sum(a.position_size_dollars for a in allocations_with_exposure)
    print(f"   New allocation: ${total_new:.2f}")
    print(f"   Total exposure would be: ${existing_exposure + total_new:.2f}")

    # Test balance update
    print("\n💰 Testing balance update...")
    new_balance = 1500.0
    allocator.update_balance(new_balance)
    print(f"✅ Balance updated to ${new_balance:.2f}")

    # Validation checks
    print("\n✅ Validation Checks:")

    # Check total allocation doesn't exceed max
    total_allocated = sum(a.position_size_dollars for a in allocations)
    max_allowed = test_balance * allocator.max_total_exposure_pct
    assert total_allocated <= max_allowed, f"Total allocation (${total_allocated:.2f}) exceeds max (${max_allowed:.2f})!"
    print(f"   ✓ Total allocation within limits (${total_allocated:.2f} <= ${max_allowed:.2f})")

    # Check individual positions don't exceed max
    max_position = test_balance * allocator.max_position_size_pct
    for alloc in allocations:
        assert alloc.position_size_dollars <= max_position, f"Position exceeds max!"
    print(f"   ✓ All positions within max size (${max_position:.2f})")

    # Check all positions meet minimum
    for alloc in allocations:
        assert alloc.position_size_dollars >= allocator.min_position_size_dollars, "Position below minimum!"
    print(f"   ✓ All positions meet minimum size (${allocator.min_position_size_dollars:.2f})")

    # Check contracts are positive integers
    for alloc in allocations:
        assert alloc.num_contracts > 0, "Non-positive contract count!"
        assert alloc.num_contracts == int(alloc.num_contracts), "Fractional contracts!"
    print("   ✓ All contract counts are positive integers")

    print("\n" + "=" * 80)
    print("✅ ALLOCATOR MODULE TEST PASSED")
    print("=" * 80)
    print("\n🚀 Ready to build executor module!")
    print()

    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_allocator()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
