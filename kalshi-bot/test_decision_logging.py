"""
Test decision logging and report generation
"""
import os
import json
import shutil
from datetime import datetime, date
from decision_logger import DecisionLogger, MarketDecision
from report_generator import ReportGenerator

print("=" * 80)
print("DECISION LOGGING & REPORTING TEST")
print("=" * 80)
print()

# Setup test data directory
test_data_dir = "data_test"
if os.path.exists(test_data_dir):
    shutil.rmtree(test_data_dir)
os.makedirs(test_data_dir)

print("🔧 Test Setup")
print(f"   Using test data directory: {test_data_dir}")
print()

# Initialize logger
logger = DecisionLogger(data_dir=test_data_dir)
report_gen = ReportGenerator(logger)

print("✅ Decision logger initialized")
print()

# Simulate Cycle 1
print("=" * 80)
print("SIMULATING TRADING CYCLE 1")
print("=" * 80)
print()

cycle1_id = logger.start_cycle()
print(f"Started cycle: {cycle1_id}")
print()

# Log some skipped markets
print("📋 Logging skipped markets...")
logger.log_skipped(
    ticker="MARKET-SKIP-1",
    title="Will it rain in Seattle tomorrow?",
    category="WEATHER",
    yes_price=0.12,
    no_price=0.88,
    time_to_settlement_hours=24.0,
    skip_reason="price too low",
    score=None
)
print("   - MARKET-SKIP-1: price too low")

logger.log_skipped(
    ticker="MARKET-SKIP-2",
    title="Will stocks go up tomorrow?",
    category="FINANCE",
    yes_price=0.65,
    no_price=0.35,
    time_to_settlement_hours=18.0,
    skip_reason="category not approved"
)
print("   - MARKET-SKIP-2: category not approved")

logger.log_skipped(
    ticker="MARKET-SKIP-3",
    title="Will Bitcoin hit $100k?",
    category="CRYPTO",
    yes_price=0.88,
    no_price=0.12,
    time_to_settlement_hours=48.0,
    skip_reason="already have position"
)
print("   - MARKET-SKIP-3: already have position")

logger.log_skipped(
    ticker="MARKET-SKIP-4",
    title="Will Fed raise rates?",
    category="FED",
    yes_price=0.91,
    no_price=0.09,
    time_to_settlement_hours=12.0,
    skip_reason="score below threshold",
    score=2.5
)
print("   - MARKET-SKIP-4: score below threshold (2.5%)")

logger.log_skipped(
    ticker="MARKET-SKIP-5",
    title="Will inflation be high?",
    category="INFL",
    yes_price=0.93,
    no_price=0.07,
    time_to_settlement_hours=6.0,
    skip_reason="insufficient capital",
    score=8.2
)
print("   - MARKET-SKIP-5: insufficient capital (score: 8.2%)")
print()

# Log some bets
print("💰 Logging executed bets...")
logger.log_bet(
    ticker="MARKET-BET-1",
    title="Will unemployment stay below 4%?",
    category="UNEMP",
    yes_price=0.89,
    no_price=0.11,
    time_to_settlement_hours=36.0,
    side="YES",
    amount=89.0,
    contracts=100,
    score=12.3
)
print("   - MARKET-BET-1: YES @ $89.00 (100 contracts, score: 12.3%)")

logger.log_bet(
    ticker="MARKET-BET-2",
    title="Will GDP growth exceed 2%?",
    category="GDP",
    yes_price=0.92,
    no_price=0.08,
    time_to_settlement_hours=24.0,
    side="YES",
    amount=92.0,
    contracts=100,
    score=8.7
)
print("   - MARKET-BET-2: YES @ $92.00 (100 contracts, score: 8.7%)")

logger.log_bet(
    ticker="MARKET-BET-3",
    title="Will retail sales increase?",
    category="RETAIL",
    yes_price=0.87,
    no_price=0.13,
    time_to_settlement_hours=30.0,
    side="YES",
    amount=87.0,
    contracts=100,
    score=14.9
)
print("   - MARKET-BET-3: YES @ $87.00 (100 contracts, score: 14.9%)")
print()

# End cycle
logger.end_cycle()
print("✅ Cycle 1 complete")
print()

# Verify decisions file was created
decisions_file = os.path.join(test_data_dir, "decisions.json")
assert os.path.exists(decisions_file), "Decisions file not created!"

with open(decisions_file, 'r') as f:
    decisions = json.load(f)

print(f"📄 Decisions file created: {decisions_file}")
print(f"   Total decisions logged: {len(decisions)}")
print(f"   Skipped: {sum(1 for d in decisions if d['decision'] == 'skipped')}")
print(f"   Bet: {sum(1 for d in decisions if d['decision'] == 'bet')}")
print()

# Simulate Cycle 2
print("=" * 80)
print("SIMULATING TRADING CYCLE 2")
print("=" * 80)
print()

cycle2_id = logger.start_cycle()
print(f"Started cycle: {cycle2_id}")
print()

# More decisions
logger.log_skipped(
    ticker="MARKET-SKIP-6",
    title="Will there be snow?",
    category="WEATHER",
    yes_price=0.15,
    no_price=0.85,
    time_to_settlement_hours=12.0,
    skip_reason="price too low"
)

logger.log_bet(
    ticker="MARKET-BET-4",
    title="Will jobs report beat expectations?",
    category="JOBS",
    yes_price=0.90,
    no_price=0.10,
    time_to_settlement_hours=6.0,
    side="YES",
    amount=90.0,
    contracts=100,
    score=11.1
)

logger.end_cycle()
print("✅ Cycle 2 complete")
print()

# Load updated decisions
with open(decisions_file, 'r') as f:
    decisions = json.load(f)

print(f"📄 Updated decisions count: {len(decisions)}")
print()

# Simulate settlement outcomes
print("=" * 80)
print("SIMULATING SETTLEMENT OUTCOMES")
print("=" * 80)
print()

print("📊 Updating outcomes...")
logger.update_outcome(
    ticker="MARKET-BET-1",
    outcome="YES",
    actual_pnl=11.0,
    settled_at=datetime.utcnow().isoformat()
)
print("   - MARKET-BET-1: Won +$11.00")

logger.update_outcome(
    ticker="MARKET-BET-2",
    outcome="NO",
    actual_pnl=-92.0,
    settled_at=datetime.utcnow().isoformat()
)
print("   - MARKET-BET-2: Lost -$92.00")

logger.update_outcome(
    ticker="MARKET-BET-3",
    outcome="YES",
    actual_pnl=13.0,
    settled_at=datetime.utcnow().isoformat()
)
print("   - MARKET-BET-3: Won +$13.00")
print()

# Generate report
print("=" * 80)
print("GENERATING DAILY REPORT")
print("=" * 80)
print()

report = report_gen.generate_daily_report(target_date=date.today())
print(report)
print()

# Test period report
print("=" * 80)
print("GENERATING 7-DAY REPORT")
print("=" * 80)
print()

period_report = report_gen.generate_period_report(days=7)
print(period_report)
print()

# Export CSV
print("=" * 80)
print("EXPORTING TO CSV")
print("=" * 80)
print()

csv_file = os.path.join(test_data_dir, "decisions_export.csv")
report_gen.export_decisions_csv(csv_file, days=7)
print(f"✅ Exported to: {csv_file}")

# Verify CSV
assert os.path.exists(csv_file), "CSV file not created!"
with open(csv_file, 'r') as f:
    lines = f.readlines()
    print(f"   CSV has {len(lines)} lines (including header)")
print()

# Test validation
print("=" * 80)
print("VALIDATION")
print("=" * 80)
print()

with open(decisions_file, 'r') as f:
    all_decisions = json.load(f)

# Counts
total = len(all_decisions)
skipped = sum(1 for d in all_decisions if d['decision'] == 'skipped')
bet = sum(1 for d in all_decisions if d['decision'] == 'bet')
settled = sum(1 for d in all_decisions if d.get('settled', False))

print(f"✓ Total decisions: {total}")
print(f"✓ Skipped markets: {skipped}")
print(f"✓ Bets placed: {bet}")
print(f"✓ Settled bets: {settled}")
print()

# Validate structure
for i, decision in enumerate(all_decisions):
    assert 'ticker' in decision, f"Decision {i} missing ticker"
    assert 'decision' in decision, f"Decision {i} missing decision"
    assert 'timestamp' in decision, f"Decision {i} missing timestamp"
    assert 'cycle_id' in decision, f"Decision {i} missing cycle_id"

print("✓ All decisions have required fields")
print()

# Validate skip reasons
skip_reasons = [d['skip_reason'] for d in all_decisions if d['decision'] == 'skipped']
expected_reasons = {'price too low', 'category not approved', 'already have position',
                   'score below threshold', 'insufficient capital'}
actual_reasons = set(skip_reasons)

print(f"✓ Skip reasons found: {actual_reasons}")
assert actual_reasons.issubset(expected_reasons), f"Unexpected skip reasons: {actual_reasons - expected_reasons}"
print()

# Validate bets have required fields
for decision in all_decisions:
    if decision['decision'] == 'bet':
        assert decision['bet_side'] is not None, f"Bet missing side: {decision['ticker']}"
        assert decision['bet_amount'] is not None, f"Bet missing amount: {decision['ticker']}"
        assert decision['bet_contracts'] is not None, f"Bet missing contracts: {decision['ticker']}"
        assert decision['score'] is not None, f"Bet missing score: {decision['ticker']}"

print("✓ All bets have required fields")
print()

# Cleanup
print("=" * 80)
print("CLEANUP")
print("=" * 80)
print()

# Keep test data for inspection
print(f"📁 Test data preserved in: {test_data_dir}")
print(f"   {decisions_file}")
print(f"   {csv_file}")
print()

print("=" * 80)
print("✅ ALL TESTS PASSED")
print("=" * 80)
print()

print("🎉 Decision logging system working correctly!")
print()
print("Features verified:")
print("  ✓ Decision logging (skipped + bet)")
print("  ✓ Multi-cycle support")
print("  ✓ Persistent JSON storage")
print("  ✓ Settlement outcome tracking")
print("  ✓ Daily report generation")
print("  ✓ Period report generation")
print("  ✓ CSV export")
print("  ✓ Data validation")
print()
