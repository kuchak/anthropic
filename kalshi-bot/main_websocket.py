"""
Kalshi Trading Bot - WebSocket Real-Time Streaming Version

Replaces polling 434+ series every 30 seconds with a single WebSocket connection.
Streams all price updates in real-time, filters for sports markets crossing 90¢.

Architecture:
- WebSocket thread: Listens for price updates, triggers on relevant markets
- Main loop: Processes triggered markets, stability tracking, allocation, execution
- Discovery: Hourly refresh to keep sports series list current
"""

import os
import sys
import time
import yaml
import asyncio
import threading
from queue import Queue
from datetime import datetime, timezone
from logger_setup import setup_logger

from kalshi_client import KalshiClient
from scorer import Scorer
from allocator import Allocator
from executor import Executor
from tracker import Tracker
from decision_logger import DecisionLogger
from report_generator import ReportGenerator
from stability_tracker import StabilityTracker
from series_discovery import SeriesDiscovery
# Using kalshi-python-unofficial library for reliable WebSocket streaming
from websocket_monitor_kalshi_lib import KalshiWebSocketMonitor
# Alternative implementation available in websocket_monitor_alt.py

logger = setup_logger("main")


class TradingBotWebSocket:
    """
    Main trading bot orchestrator with WebSocket streaming.

    Uses WebSocket to monitor ALL markets in real-time.
    Triggers on sports markets crossing 90¢ and expiring within 3 hours.
    """

    def __init__(self, config: dict, dry_run: bool = True):
        self.config = config
        self.dry_run = dry_run

        # Queue for triggered markets from WebSocket
        self.triggered_markets = Queue()

        # Initialize components
        logger.info("=" * 80)
        logger.info("INITIALIZING KALSHI TRADING BOT - WEBSOCKET VERSION")
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

        # Series Discovery
        logger.info("\n🔬 Initializing series discovery...")
        self.series_discovery = SeriesDiscovery()
        logger.info("✅ Series discovery ready")

        # Run initial discovery
        logger.info("\n🔍 Running initial series discovery...")
        discovery_pages = config.get('series_discovery_pages', 20)
        self.series_discovery.discover_series(max_pages=discovery_pages)
        stats = self.series_discovery.get_stats()
        logger.info(f"✅ Discovered {stats['total_series']} series across {stats['total_categories']} categories")
        logger.info(f"   Sports series: {stats['sports_series_count']}")

        # WebSocket Monitor (using kalshi-python-unofficial library)
        logger.info("\n🌐 Initializing WebSocket monitor...")
        self.ws_monitor = KalshiWebSocketMonitor(config, self.series_discovery)
        logger.info("✅ WebSocket monitor ready (kalshi-python-unofficial)")

        # Scorer
        logger.info("\n🎯 Initializing scorer...")
        self.scorer = Scorer(config)
        logger.info("✅ Scorer ready")

        # Stability Tracker
        logger.info("\n⏱️  Initializing stability tracker...")
        self.stability_tracker = StabilityTracker(config)
        logger.info("✅ Stability tracker ready")

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

        # Last discovery time
        self.last_discovery_time = datetime.now(timezone.utc)

        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL SYSTEMS INITIALIZED (WEBSOCKET STREAMING)")
        logger.info("=" * 80)

    async def on_market_triggered(self, ticker: str, yes_price: float, no_price: float):
        """
        Callback when WebSocket detects a market crossing 90¢.

        Args:
            ticker: Market ticker
            yes_price: Yes price in dollars
            no_price: No price in dollars
        """
        logger.info(f"📥 Market triggered: {ticker} | YES={yes_price:.2f} NO={no_price:.2f}")

        # Add to queue for main loop processing
        self.triggered_markets.put({
            'ticker': ticker,
            'yes_price': yes_price,
            'no_price': no_price,
            'timestamp': datetime.now(timezone.utc)
        })

    def start_websocket_thread(self):
        """Start WebSocket monitor in background thread"""

        def run_websocket():
            """Run WebSocket in async loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(
                    self.ws_monitor.run_monitor(self.on_market_triggered)
                )
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
            finally:
                loop.close()

        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        logger.info("✅ WebSocket thread started")

        return thread

    def check_hourly_discovery(self):
        """Check if it's time to rediscover series (every hour)"""
        hours_since = (datetime.now(timezone.utc) - self.last_discovery_time).total_seconds() / 3600

        if hours_since >= 1.0:
            logger.info("\n🔬 Hourly Series Rediscovery")
            logger.info("-" * 80)

            discovery_pages = self.config.get('series_discovery_pages', 20)
            self.series_discovery.discover_series(max_pages=discovery_pages)
            stats = self.series_discovery.get_stats()

            logger.info(f"✅ Rediscovered {stats['total_series']} series, {stats['sports_series_count']} sports")
            self.last_discovery_time = datetime.now(timezone.utc)

    def process_triggered_markets(self):
        """Process markets triggered by WebSocket"""

        cycle_id = self.decision_logger.start_cycle()

        logger.info("\n" + "=" * 80)
        logger.info(f"PROCESSING TRIGGERED MARKETS - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"Cycle ID: {cycle_id}")
        logger.info("=" * 80)

        # Collect all triggered markets from queue
        triggered = []
        while not self.triggered_markets.empty():
            market = self.triggered_markets.get()
            triggered.append(market)

        if not triggered:
            logger.debug("No triggered markets in queue")
            self.decision_logger.end_cycle()
            return

        logger.info(f"📊 {len(triggered)} markets triggered by WebSocket")

        # Fetch full market data for each triggered market
        markets = []
        for t in triggered:
            ticker = t['ticker']

            try:
                # Fetch full market data
                market_data = self.client.get_market(ticker)

                if not market_data:
                    logger.debug(f"Could not fetch data for {ticker}")
                    continue

                # Parse market
                from models import Market
                from dateutil.parser import parse as parse_datetime

                yes_price = t['yes_price']
                no_price = t['no_price']

                market = Market(
                    ticker=ticker,
                    title=market_data['title'],
                    category=ticker.split('-')[0],
                    settlement_time=parse_datetime(market_data['close_time']),
                    status=market_data['status'],
                    best_yes_price=yes_price,
                    best_no_price=no_price,
                    best_yes_size=0,
                    best_no_size=0,
                    volume_24h=float(market_data.get('volume_24h_fp', 0) or 0)
                )

                markets.append(market)

            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")
                continue

        logger.info(f"✅ Fetched data for {len(markets)} markets")

        if not markets:
            logger.info("⚠️  No valid markets after fetch")
            self.decision_logger.end_cycle()
            return

        # Score opportunities
        logger.info("\n🎯 Scoring Opportunities")
        logger.info("-" * 80)

        opportunities = self.scorer.score_markets(markets)
        logger.info(f"✅ Found {len(opportunities)} valid opportunities")

        if not opportunities:
            logger.info("⚠️  No valid opportunities")
            self.decision_logger.end_cycle()
            return

        # Stability Check
        logger.info("\n⏱️  Stability Check")
        logger.info("-" * 80)

        stable_opportunities = []
        for opp in opportunities:
            is_stable = self.stability_tracker.check_market(
                ticker=opp.market.ticker,
                current_price=opp.entry_price
            )

            if is_stable:
                stable_opportunities.append(opp)
            else:
                status = self.stability_tracker.get_wait_status(opp.market.ticker)
                if status:
                    reason = f"waiting {status['remaining_minutes']:.1f}m more"
                else:
                    reason = "just started waiting"

                logger.debug(f"  {opp.market.ticker}: {reason}")

        logger.info(f"✅ {len(stable_opportunities)}/{len(opportunities)} opportunities stable")

        if not stable_opportunities:
            logger.info("⚠️  No stable opportunities yet")
            self.decision_logger.end_cycle()
            return

        # Allocate positions
        logger.info("\n💵 Position Allocation")
        logger.info("-" * 80)

        current_exposure = self.tracker.get_total_exposure()
        existing_tickers = list(self.tracker.positions.keys())

        # Filter out existing positions
        stable_opportunities = [opp for opp in stable_opportunities if opp.market.ticker not in existing_tickers]

        if not stable_opportunities:
            logger.info("⚠️  All opportunities already have positions")
            self.decision_logger.end_cycle()
            return

        allocations = self.allocator.allocate_positions(stable_opportunities, current_exposure)
        logger.info(f"✅ Allocated {len(allocations)} positions")

        if not allocations:
            logger.info("⚠️  No allocations made")
            self._update_portfolio()
            self.decision_logger.end_cycle()
            return

        # Execute trades
        logger.info("\n🎬 Trade Execution")
        logger.info("-" * 80)

        executions = self.executor.execute_allocations(allocations)
        logger.info(f"✅ Executed {len(executions)} trades")

        for execution in executions:
            if execution.status == "success":
                # Reset stability tracking
                self.stability_tracker.reset_market(execution.ticker)
                # Reset WebSocket trigger
                self.ws_monitor.reset_trigger(execution.ticker)

        self.tracker.add_executions(executions)

        # Update portfolio
        self._update_portfolio()

        # Cleanup old stability tracking
        cleaned = self.stability_tracker.cleanup_old_tracking(max_age_hours=6)
        if cleaned > 0:
            logger.debug(f"🧹 Cleaned up {cleaned} old stability records")

        self.decision_logger.end_cycle()

        logger.info("\n" + "=" * 80)
        logger.info("✅ CYCLE COMPLETE")
        logger.info("=" * 80)

    def _update_portfolio(self):
        """Update portfolio positions and check settlements"""

        logger.info("\n📊 Portfolio Update")
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

    def run_continuous(self):
        """Run continuous trading loop with WebSocket streaming"""

        logger.info("\n🚀 Starting WebSocket streaming bot")
        logger.info("   One WebSocket replaces 434+ REST API calls per cycle")
        logger.info("   Real-time price monitoring for all markets")
        logger.info("   Press Ctrl+C to stop\n")

        # Start WebSocket thread
        ws_thread = self.start_websocket_thread()

        # Give WebSocket time to connect
        time.sleep(3)

        try:
            while True:
                # Check hourly discovery
                self.check_hourly_discovery()

                # Process any triggered markets
                if not self.triggered_markets.empty():
                    self.process_triggered_markets()

                # Sleep before next check (10 seconds)
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Shutdown requested by user")
            self._shutdown()

    def _shutdown(self):
        """Clean shutdown"""

        logger.info("\n" + "=" * 80)
        logger.info("SHUTTING DOWN")
        logger.info("=" * 80)

        logger.info("\n📊 Final Portfolio Summary:")
        self.tracker.print_summary()

        logger.info("\n✅ Shutdown complete")
        logger.info("=" * 80)


def main():
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(
        description="Kalshi Trading Bot - WebSocket Streaming Version"
    )
    parser.add_argument('--live', action='store_true', help='LIVE mode (real money!)')
    parser.add_argument('--dry-run', action='store_true', default=True, help='DRY-RUN mode (safe)')

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

    # Add API credentials from environment
    config['kalshi_api_key_id'] = os.getenv('KALSHI_API_KEY_ID')
    config['kalshi_private_key_path'] = os.getenv('KALSHI_PRIVATE_KEY_PATH')

    try:
        bot = TradingBotWebSocket(config, dry_run=dry_run)
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
