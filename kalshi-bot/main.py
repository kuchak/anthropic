"""
Kalshi Trading Bot - Main Orchestration Loop

High-level strategy backed by 90%+ accuracy backtests:
- Scan for 85-98¢ contracts in approved categories
- Score by expected profit using empirical win rates
- Size positions using Kelly criterion (25% Kelly)
- Execute in dry-run or live mode
- Track settlements and P&L

Usage:
    python main.py --dry-run           # Safe mode (default)
    python main.py --live              # Real trading mode
    python main.py --once              # Run once and exit
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

logger = setup_logger("main")


class TradingBot:
    """
    Main trading bot orchestrator

    Coordinates all modules in a continuous loop:
    1. Scan for markets
    2. Score opportunities
    3. Allocate positions
    4. Execute trades
    5. Track portfolio
    6. Monitor settlements
    """

    def __init__(self, config: dict, dry_run: bool = True):
        self.config = config
        self.dry_run = dry_run

        # Initialize components
        logger.info("=" * 80)
        logger.info("INITIALIZING KALSHI TRADING BOT")
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

        # Get initial balance
        logger.info("\n💰 Fetching account balance...")
        balance_data = self.client.get_balance()

        if balance_data and not dry_run:
            self.balance = balance_data.get('balance', 0) / 100.0  # Convert cents to dollars
            logger.info(f"✅ Balance: ${self.balance:.2f}")
        else:
            # Use simulated balance for dry-run or if API fails
            self.balance = config.get('simulated_balance', 1000.0)
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

        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL SYSTEMS INITIALIZED")
        logger.info("=" * 80)

    def run_once(self) -> None:
        """Run one complete trading cycle"""

        logger.info("\n" + "=" * 80)
        logger.info(f"TRADING CYCLE - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)

        # Step 1: Scan for markets
        logger.info("\n📡 Step 1: Market Discovery")
        logger.info("-" * 80)

        # Get existing position tickers to avoid duplicates
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

        if not watchlist:
            logger.info("⚠️  No markets on watchlist, skipping cycle")
            return

        # Step 2: Score opportunities
        logger.info("\n🎯 Step 2: Opportunity Scoring")
        logger.info("-" * 80)

        opportunities = self.scorer.score_markets(watchlist)
        logger.info(f"✅ Found {len(opportunities)} valid opportunities")

        if not opportunities:
            logger.info("⚠️  No valid opportunities, skipping cycle")
            return

        # Show top opportunities
        top_5 = opportunities[:5]
        logger.info("\n📊 Top 5 Opportunities:")
        for i, opp in enumerate(top_5, 1):
            logger.info(f"   {i}. {opp.market.ticker}")
            logger.info(f"      {opp.side} @ ${opp.entry_price:.2f} - ROI: {opp.expected_roi:.1f}%")

        # Step 3: Allocate positions
        logger.info("\n💵 Step 3: Position Allocation")
        logger.info("-" * 80)

        current_exposure = self.tracker.get_total_exposure()
        logger.info(f"Current exposure: ${current_exposure:.2f}")

        allocations = self.allocator.allocate_positions(opportunities, current_exposure)
        logger.info(f"✅ Allocated {len(allocations)} positions")

        if not allocations:
            logger.info("⚠️  No allocations made (capital constraints or opportunity quality)")
            # Still update existing positions
            self._update_portfolio()
            return

        # Show allocations
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

        # Add to tracker
        self.tracker.add_executions(executions)

        # Step 5: Update portfolio
        self._update_portfolio()

        logger.info("\n" + "=" * 80)
        logger.info("✅ CYCLE COMPLETE")
        logger.info("=" * 80)

    def _update_portfolio(self) -> None:
        """Update portfolio positions and check settlements"""

        logger.info("\n📊 Step 5: Portfolio Update")
        logger.info("-" * 80)

        # Update positions
        self.tracker.update_positions()

        # Get current state
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

        logger.info("\n🚀 Starting continuous trading loop")
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

                # Wait before next cycle
                sleep_time = self.config.get('cycle_interval_seconds', 180)  # 3 minutes default
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

        # Print final summary
        logger.info("\n📊 Final Portfolio Summary:")
        self.tracker.print_summary()

        logger.info("\n✅ Shutdown complete")
        logger.info("=" * 80)


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Kalshi Trading Bot - Automated high-probability contract trading"
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Run in LIVE mode (real money at risk!)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Run in DRY-RUN mode (safe, no real trades)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (instead of continuous loop)'
    )

    args = parser.parse_args()

    # Determine mode
    dry_run = not args.live

    if not dry_run:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: LIVE MODE REQUESTED")
        print("=" * 80)
        print("\nYou are about to run the bot in LIVE mode.")
        print("This will place REAL orders with REAL money on Kalshi.")
        print("\nAre you ABSOLUTELY sure you want to continue?")
        response = input("\nType 'YES' in all caps to confirm: ")

        if response != "YES":
            print("\n❌ Live mode cancelled")
            return 1

        print("\n✅ Live mode confirmed - starting bot...\n")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize bot
    try:
        bot = TradingBot(config, dry_run=dry_run)

        # Run
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
    # Ensure API keys are set
    if not os.getenv('KALSHI_API_KEY_ID') or not os.getenv('KALSHI_PRIVATE_KEY_PATH'):
        print("\n❌ Error: API credentials not configured")
        print("\nPlease set environment variables:")
        print("  export KALSHI_API_KEY_ID='your-key-id'")
        print("  export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'")
        print()
        sys.exit(1)

    sys.exit(main())
