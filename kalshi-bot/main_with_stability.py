"""
Kalshi Trading Bot - Main Orchestration Loop WITH STABILITY TRACKING

CRITICAL ADDITION: Enforces ticker-specific wait times before betting.
Prevents betting on temporary price spikes that drop back below 90¢.

Changes from original main.py:
1. Added StabilityTracker initialization
2. Added Step 2.5: Stability filtering before allocation
3. Reset stability tracking after successful execution

From backtest: 58% of markets drop back - this prevents those losing bets.
"""
import os
import sys
import time
import yaml
import argparse
from datetime import datetime
from logger_setup import setup_logger

from kalshi_client import KalshiClient
from scanner import Scanner
from scorer import Scorer
from allocator import Allocator
from executor import Executor
from tracker import Tracker
from decision_logger import DecisionLogger
from report_generator import ReportGenerator
from stability_tracker import StabilityTracker  # NEW IMPORT

logger = setup_logger("main")


class TradingBot:
    """
    Main trading bot orchestrator with stability tracking.

    Coordinates all modules in a continuous loop:
    1. Scan for markets
    2. Score opportunities
    3. **NEW** Check stability (wait for price to hold)
    4. Allocate positions
    5. Execute trades
    6. Track portfolio
    7. Monitor settlements
    """

    def __init__(self, config: dict, dry_run: bool = True):
        self.config = config
        self.dry_run = dry_run

        # Initialize components
        logger.info("=" * 80)
        logger.info("INITIALIZING KALSHI TRADING BOT WITH STABILITY TRACKING")
        logger.info("=" * 80)

        mode = "DRY-RUN (SAFE)" if dry_run else "🔴 LIVE (REAL MONEY)"
        logger.info(f"\n🤖 Mode: {mode}")

        # API Client
        logger.info("\n📡 Initializing API client...")
        self.client = KalshiClient(config)

        if not self.client.test_connection():
            logger.error("❌ API connection failed!")
            raise Exception("Failed to connect to Kalshi API")

        logger.info("✅ API client connected")

        # Scanner
        logger.info("\n🔍 Initializing scanner...")
        self.scanner = Scanner(self.client, config)
        logger.info("✅ Scanner ready")

        # Scorer
        logger.info("\n🎯 Initializing scorer...")
        self.scorer = Scorer(config)
        logger.info("✅ Scorer ready")

        # Stability Tracker (NEW!)
        logger.info("\n⏱️  Initializing stability tracker...")
        self.stability_tracker = StabilityTracker(config)
        logger.info("✅ Stability tracker ready")
        logger.info(f"   Ticker-specific wait times: {len(config.get('series_ticker_wait_times', {}))} tickers")

        # Get initial balance
        logger.info("\n💰 Fetching account balance...")
        balance_data = self.client.get_balance()

        if balance_data and not dry_run:
            self.balance = balance_data.get('balance', 0) / 100.0
            logger.info(f"✅ Balance: ${self.balance:.2f}")
        else:
            self.balance = config.get('starting_bankroll', 10000.0)
            logger.info(f"✅ Using simulated balance: ${self.balance:.2f}")

        # Allocator
        logger.info("\n💵 Initializing allocator...")
        self.allocator = Allocator(config, self.balance)
        logger.info("✅ Allocator ready")

        # Executor
        logger.info("\n🎬 Initializing executor...")
        self.executor = Executor(self.client, config, dry_run)
        logger.info("✅ Executor ready")

        # Tracker
        logger.info("\n📊 Initializing tracker...")
        self.tracker = Tracker(self.client, dry_run)
        self.tracker.initialize_balance(self.balance)
        logger.info("✅ Tracker ready")

        # Decision Logger
        logger.info("\n📝 Initializing decision logger...")
        self.decision_logger = DecisionLogger(data_dir="data")
        self.report_generator = ReportGenerator(self.decision_logger)
        logger.info("✅ Decision logger ready")

        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL SYSTEMS INITIALIZED (WITH STABILITY TRACKING)")
        logger.info("=" * 80)

    def run_once(self) -> None:
        """Run one complete trading cycle with stability checks"""

        cycle_id = self.decision_logger.start_cycle()

        logger.info("\n" + "=" * 80)
        logger.info(f"TRADING CYCLE - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"Cycle ID: {cycle_id}")
        logger.info("=" * 80)

        # Step 1: Scan for markets
        logger.info("\n📡 Step 1: Market Discovery")
        logger.info("-" * 80)

        existing_tickers = list(self.tracker.positions.keys())

        if self.scanner.should_run_slow_scan():
            logger.info("Running slow scan (full discovery)...")
            self.scanner.slow_scan(existing_position_tickers=existing_tickers)
        elif self.scanner.should_run_fast_scan():
            logger.info("Running fast scan (price updates)...")
            self.scanner.fast_scan(existing_position_tickers=existing_tickers)
        else:
            logger.info("Scan not needed yet, using cached watchlist")

        watchlist = self.scanner.get_watchlist()
        logger.info(f"✅ Watchlist: {len(watchlist)} markets")

        for ticker in existing_tickers:
            self.decision_logger.log_skipped(
                ticker=ticker,
                title="(Existing position)",
                category="",
                yes_price=0.0,
                no_price=0.0,
                time_to_settlement_hours=0.0,
                skip_reason="already have position"
            )

        if not watchlist:
            logger.info("⚠️  No markets on watchlist, skipping cycle")
            self.decision_logger.end_cycle()
            return

        # Step 2: Score opportunities
        logger.info("\n🎯 Step 2: Opportunity Scoring")
        logger.info("-" * 80)

        opportunities = self.scorer.score_markets(watchlist)
        logger.info(f"✅ Found {len(opportunities)} valid opportunities")

        scored_tickers = {opp.market.ticker for opp in opportunities}
        for market in watchlist:
            if market.ticker not in scored_tickers:
                self.decision_logger.log_skipped(
                    ticker=market.ticker,
                    title=market.title,
                    category=market.category,
                    yes_price=market.best_yes_price,
                    no_price=market.best_no_price,
                    time_to_settlement_hours=(market.settlement_time - datetime.utcnow()).total_seconds() / 3600,
                    skip_reason="score below threshold"
                )

        if not opportunities:
            logger.info("⚠️  No valid opportunities, skipping cycle")
            self.decision_logger.end_cycle()
            return

        # **NEW** Step 2.5: Stability Check
        logger.info("\n⏱️  Step 2.5: Stability Check")
        logger.info("-" * 80)
        logger.info("Checking if markets have held price >= 90¢ for required wait time...")

        stable_opportunities = []
        for opp in opportunities:
            # Check if market is stable (held >= 90¢ for required wait time)
            is_stable = self.stability_tracker.check_market(
                ticker=opp.market.ticker,
                current_price=opp.entry_price
            )

            if is_stable:
                stable_opportunities.append(opp)
            else:
                # Log why we're not betting yet
                status = self.stability_tracker.get_wait_status(opp.market.ticker)
                if status:
                    reason = f"waiting {status['remaining_minutes']:.1f}m more (required: {status['required_wait_minutes']}m)"
                else:
                    reason = "just started waiting"

                self.decision_logger.log_skipped(
                    ticker=opp.market.ticker,
                    title=opp.market.title,
                    category=opp.market.category,
                    yes_price=opp.market.best_yes_price,
                    no_price=opp.market.best_no_price,
                    time_to_settlement_hours=opp.time_to_settlement_hours,
                    skip_reason=f"price not stable ({reason})"
                )

        logger.info(f"✅ {len(stable_opportunities)}/{len(opportunities)} opportunities passed stability check")

        # Show stability summary
        summary = self.stability_tracker.get_summary()
        logger.info(f"   Tracking {summary['tracked_markets']} markets total")
        logger.info(f"   {summary['ready_markets']} ready, {summary['waiting_markets']} still waiting")

        if not stable_opportunities:
            logger.info("⚠️  No stable opportunities yet, will check again next cycle")
            self.decision_logger.end_cycle()
            return

        # Show top stable opportunities
        top_5 = stable_opportunities[:5]
        logger.info("\n📊 Top 5 Stable Opportunities:")
        for i, opp in enumerate(top_5, 1):
            logger.info(f"   {i}. {opp.market.ticker}")
            logger.info(f"      {opp.side} @ ${opp.entry_price:.2f} - ROI: {opp.expected_roi:.1f}%")

        # Step 3: Allocate positions
        logger.info("\n💵 Step 3: Position Allocation")
        logger.info("-" * 80)

        current_exposure = self.tracker.get_total_exposure()
        logger.info(f"Current exposure: ${current_exposure:.2f}")

        allocations = self.allocator.allocate_positions(stable_opportunities, current_exposure)
        logger.info(f"✅ Allocated {len(allocations)} positions")

        allocated_tickers = {alloc.opportunity.market.ticker for alloc in allocations}
        for opp in stable_opportunities:
            if opp.market.ticker not in allocated_tickers:
                self.decision_logger.log_skipped(
                    ticker=opp.market.ticker,
                    title=opp.market.title,
                    category=opp.market.category,
                    yes_price=opp.market.best_yes_price,
                    no_price=opp.market.best_no_price,
                    time_to_settlement_hours=(opp.market.settlement_time - datetime.utcnow()).total_seconds() / 3600,
                    skip_reason="insufficient capital",
                    score=opp.expected_roi
                )

        if not allocations:
            logger.info("⚠️  No allocations made (capital constraints)")
            self._update_portfolio()
            self.decision_logger.end_cycle()
            return

        logger.info("\n📋 Position Allocations:")
        for i, alloc in enumerate(allocations, 1):
            logger.info(f"   {i}. {alloc.opportunity.market.ticker}")
            logger.info(f"      {alloc.num_contracts} contracts @ ${alloc.opportunity.entry_price:.2f}")
            logger.info(f"      Total: ${alloc.position_size_dollars:.2f}")

        # Step 4: Execute trades
        logger.info("\n🎬 Step 4: Trade Execution")
        logger.info("-" * 80)

        executions = self.executor.execute_allocations(allocations)
        logger.info(f"✅ Executed {len(executions)} trades")

        for execution in executions:
            if execution.status == "success":
                alloc = next((a for a in allocations if a.opportunity.market.ticker == execution.ticker), None)
                if alloc:
                    market = alloc.opportunity.market
                    self.decision_logger.log_bet(
                        ticker=market.ticker,
                        title=market.title,
                        category=market.category,
                        yes_price=market.best_yes_price,
                        no_price=market.best_no_price,
                        time_to_settlement_hours=(market.settlement_time - datetime.utcnow()).total_seconds() / 3600,
                        side=execution.side,
                        amount=execution.total_cost,
                        contracts=execution.num_contracts,
                        score=alloc.opportunity.expected_roi
                    )

                # **NEW** Reset stability tracking after successful execution
                self.stability_tracker.reset_market(execution.ticker)
                logger.debug(f"🔄 Reset stability tracking for {execution.ticker}")

        self.tracker.add_executions(executions)

        # Step 5: Update portfolio
        self._update_portfolio()

        # Cleanup old stability tracking (once per cycle)
        cleaned = self.stability_tracker.cleanup_old_tracking(max_age_hours=6)
        if cleaned > 0:
            logger.debug(f"🧹 Cleaned up {cleaned} old stability tracking records")

        self.decision_logger.end_cycle()

        logger.info("\n" + "=" * 80)
        logger.info("✅ CYCLE COMPLETE")
        logger.info("=" * 80)

    def _update_portfolio(self) -> None:
        """Update portfolio positions and check settlements"""

        logger.info("\n📊 Step 5: Portfolio Update")
        logger.info("-" * 80)

        self.tracker.update_positions()
        report = self.tracker.get_performance_report()

        logger.info(f"\n💰 Portfolio Status:")
        logger.info(f"   Balance: ${report['current_balance']:.2f}")
        logger.info(f"   Active Positions: {report['active_positions']}")
        logger.info(f"   Settled Positions: {report['settled_positions']}")
        logger.info(f"   Total Exposure: ${report['total_exposure']:.2f}")
        logger.info(f"   Total P&L: ${report['total_pnl']:+.2f} ({report['total_return_pct']:+.1f}%)")

        if report['settled_positions'] > 0:
            logger.info(f"   Win Rate: {report['win_rate']:.1f}%")
            logger.info(f"   Wins: {report['wins']}, Losses: {report['losses']}")

    def run_continuous(self) -> None:
        """Run continuous trading loop"""

        logger.info("\n🚀 Starting continuous trading loop WITH STABILITY TRACKING")
        logger.info("   Markets must hold >= 90¢ for 1-5 minutes before betting")
        logger.info("   Press Ctrl+C to stop\n")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1

                try:
                    self.run_once()

                except Exception as e:
                    logger.error(f"❌ Error in trading cycle: {e}")
                    import traceback
                    traceback.print_exc()

                sleep_time = self.config.get('cycle_interval_seconds', 180)
                logger.info(f"\n💤 Sleeping {sleep_time}s until next cycle...\n")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Shutdown requested by user")
            self._shutdown()

    def _shutdown(self) -> None:
        """Clean shutdown"""

        logger.info("\n" + "=" * 80)
        logger.info("SHUTTING DOWN")
        logger.info("=" * 80)

        logger.info("\n📊 Final Portfolio Summary:")
        self.tracker.print_summary()

        logger.info("\n✅ Shutdown complete")
        logger.info("=" * 80)


# Rest of main() function stays the same...
def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Kalshi Trading Bot - Automated trading with stability tracking"
    )
    parser.add_argument('--live', action='store_true', help='LIVE mode (real money!)')
    parser.add_argument('--dry-run', action='store_true', default=True, help='DRY-RUN mode (safe)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')

    args = parser.parse_args()

    dry_run = not args.live

    if not dry_run:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: LIVE MODE REQUESTED")
        print("=" * 80)
        response = input("\nType 'YES' in all caps to confirm: ")
        if response != "YES":
            print("\n❌ Live mode cancelled")
            return 1

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    try:
        bot = TradingBot(config, dry_run=dry_run)

        if args.once:
            logger.info("\n🏃 Running once and exiting...")
            bot.run_once()
            bot._shutdown()
        else:
            bot.run_continuous()

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    if not os.getenv('KALSHI_API_KEY_ID') or not os.getenv('KALSHI_PRIVATE_KEY_PATH'):
        print("\n❌ Error: API credentials not configured")
        print("\nPlease set environment variables:")
        print("  export KALSHI_API_KEY_ID='your-key-id'")
        print("  export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'")
        print()
        sys.exit(1)

    sys.exit(main())
