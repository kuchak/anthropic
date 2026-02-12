"""
Test script for Scorer module
"""
import yaml
from datetime import datetime, timedelta
from logger_setup import setup_logger
from models import Market
from scorer import Scorer

logger = setup_logger("test_scorer")


def create_test_market(ticker: str, title: str, yes_price: float, settlement_hours: float) -> Market:
    """Create a test market"""
    return Market(
        ticker=ticker,
        title=title,
        category="test",
        settlement_time=datetime.utcnow() + timedelta(hours=settlement_hours),
        status="open",
        best_yes_price=yes_price,
        best_no_price=1.0 - yes_price,
        best_yes_size=100,
        best_no_size=100
    )


def test_scorer():
    """Test scorer functionality"""

    print("=" * 80)
    print("SCORER MODULE TEST")
    print("=" * 80)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize scorer
    print("\n🎯 Initializing scorer...")
    scorer = Scorer(config)
    print("✅ Scorer initialized")
    print(f"   Default accuracy: {scorer.default_accuracy * 100:.1f}%")

    # Create test markets with various characteristics
    print("\n📊 Creating test markets...")
    test_markets = [
        # High confidence range (85-89¢) - should score well
        create_test_market("TEST-HIGH-1", "High confidence market", 0.87, 2.0),

        # Mid confidence range (90-95¢) - should score moderately
        create_test_market("TEST-MID-1", "Mid confidence market", 0.92, 3.0),

        # Edge of range (95-98¢) - should score lower
        create_test_market("TEST-EDGE-1", "Edge of range market", 0.96, 1.5),

        # Very short settlement - should get time penalty
        create_test_market("TEST-SHORT-1", "Very short settlement", 0.88, 0.5),

        # Very long settlement - should get time penalty
        create_test_market("TEST-LONG-1", "Long settlement", 0.87, 8.0),

        # Out of range (too cheap) - should be filtered
        create_test_market("TEST-CHEAP-1", "Too cheap", 0.45, 2.0),

        # Out of range (too expensive) - should be filtered
        create_test_market("TEST-EXPENSIVE-1", "Too expensive", 0.99, 2.0),
    ]

    print(f"   Created {len(test_markets)} test markets")

    # Score all markets
    print("\n🎯 Scoring markets...")
    opportunities = scorer.score_markets(test_markets)
    print(f"✅ Scored {len(test_markets)} markets → {len(opportunities)} valid opportunities")

    # Display results
    if opportunities:
        print("\n📋 Ranked Opportunities:")
        for i, opp in enumerate(opportunities, 1):
            print(f"\n   {i}. {opp.market.ticker}")
            print(f"      Side: {opp.side}")
            print(f"      Entry Price: ${opp.entry_price:.2f}")
            print(f"      Win Probability: {opp.win_probability * 100:.1f}%")
            print(f"      Expected Profit: ${opp.expected_profit:.4f}")
            print(f"      Expected ROI: {opp.expected_roi:.2f}%")
            print(f"      Rank Score: {opp.rank_score:.2f}")
            print(f"      Time to Settlement: {opp.time_to_settlement_hours:.1f}h")

        # Get stats
        print("\n📊 Opportunity Statistics:")
        stats = scorer.get_stats(opportunities)
        print(f"   Total opportunities: {stats['total_opportunities']}")
        print(f"   Avg Expected ROI: {stats['avg_expected_roi']:.2f}%")
        print(f"   Avg Win Probability: {stats['avg_win_probability'] * 100:.1f}%")
        print(f"   Avg Settlement Time: {stats['avg_time_to_settlement_hours']:.1f}h")
        print(f"   Best ROI: {stats['best_roi']:.2f}%")
        print(f"   Worst ROI: {stats['worst_roi']:.2f}%")

    # Test get_top_opportunities
    print("\n🏆 Testing get_top_opportunities (limit=3)...")
    top_3 = scorer.get_top_opportunities(test_markets, limit=3)
    print(f"✅ Retrieved top {len(top_3)} opportunities")
    for i, opp in enumerate(top_3, 1):
        print(f"   {i}. {opp.market.ticker} - ROI: {opp.expected_roi:.2f}%")

    # Validation checks
    print("\n✅ Validation Checks:")

    # Check that fully out-of-range markets are excluded
    # Note: TEST-CHEAP-1 YES side is out of range, but NO side ($0.55) is valid
    # TEST-EXPENSIVE-1 has YES at $0.99, so NO is $0.01 (also out of range)
    expensive_tickers = {"TEST-EXPENSIVE-1"}
    remaining_tickers = {opp.market.ticker for opp in opportunities}
    assert "TEST-EXPENSIVE-1" not in remaining_tickers, "Expensive market not filtered!"
    print("   ✓ Price filters working correctly (both sides checked)")

    # Check that opportunities are sorted by rank
    ranks = [opp.rank_score for opp in opportunities]
    assert ranks == sorted(ranks, reverse=True), "Opportunities not sorted by rank!"
    print("   ✓ Opportunities sorted by rank score")

    # Check that all valid opportunities have positive expected ROI
    assert all(opp.expected_roi > 0 for opp in opportunities), "Negative ROI in results!"
    print("   ✓ All opportunities have positive expected ROI")

    print("\n" + "=" * 80)
    print("✅ SCORER MODULE TEST PASSED")
    print("=" * 80)
    print("\n🚀 Ready to build allocator module!")
    print()

    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_scorer()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
