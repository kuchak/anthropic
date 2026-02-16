#!/usr/bin/env python3
"""
Test script for alternative WebSocket monitor using websocket-client library
"""

import os
import sys
import asyncio
import yaml
import logging
from datetime import datetime

from websocket_monitor_alt import WebSocketMonitorAlt
from series_discovery import SeriesDiscovery

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_market_triggered(ticker: str, yes_price: float, no_price: float):
    """Callback for triggered markets"""
    logger.info(f"🎯 TRIGGERED: {ticker} | YES=${yes_price:.2f} NO=${no_price:.2f}")


async def main():
    """Test WebSocket connection"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Add API credentials
    config['kalshi_api_key_id'] = os.getenv('KALSHI_API_KEY_ID')
    config['kalshi_private_key_path'] = os.getenv('KALSHI_PRIVATE_KEY_PATH')

    if not config['kalshi_api_key_id'] or not config['kalshi_private_key_path']:
        logger.error("❌ API credentials not configured")
        return 1

    logger.info("=" * 80)
    logger.info("Testing WebSocket Monitor (websocket-client library)")
    logger.info("=" * 80)

    # Initialize series discovery
    logger.info("\n🔬 Initializing series discovery...")
    series_discovery = SeriesDiscovery()
    series_discovery.discover_series(max_pages=5)
    stats = series_discovery.get_stats()
    logger.info(f"✅ Discovered {stats['total_series']} series, {stats['sports_series_count']} sports")

    # Initialize WebSocket monitor
    logger.info("\n🌐 Initializing WebSocket monitor (websocket-client)...")
    monitor = WebSocketMonitorAlt(config, series_discovery)
    logger.info("✅ Monitor ready")

    # Start monitoring
    logger.info("\n🚀 Starting WebSocket connection...")
    logger.info("   This will test authentication and connection")
    logger.info("   Press Ctrl+C to stop\n")

    try:
        await monitor.run(on_market_triggered)
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Test stopped by user")
        return 0


if __name__ == "__main__":
    if not os.getenv('KALSHI_API_KEY_ID') or not os.getenv('KALSHI_PRIVATE_KEY_PATH'):
        print("\n❌ Error: API credentials not configured")
        print("\nPlease set environment variables:")
        print("  export KALSHI_API_KEY_ID='your-key-id'")
        print("  export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'")
        print()
        sys.exit(1)

    sys.exit(asyncio.run(main()))
