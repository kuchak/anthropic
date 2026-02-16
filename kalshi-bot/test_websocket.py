"""
Test WebSocket connection and streaming.

Connects to Kalshi WebSocket, subscribes to ticker channel,
and prints first 10 price updates.
"""

import asyncio
import yaml
from websocket_monitor import WebSocketMonitor
from series_discovery import SeriesDiscovery
from logger_setup import setup_logger

logger = setup_logger("test_websocket")


async def test_websocket():
    """Test WebSocket connection and streaming"""

    print("=" * 80)
    print("TESTING KALSHI WEBSOCKET CONNECTION")
    print("=" * 80)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Run discovery first (needed for sports series filtering)
    print("\n1. Running series discovery...")
    discovery = SeriesDiscovery()
    discovery.discover_series(max_pages=5)  # Quick discovery
    stats = discovery.get_stats()
    print(f"   ✓ Discovered {stats['sports_series_count']} sports series")

    # Create WebSocket monitor
    print("\n2. Creating WebSocket monitor...")
    monitor = WebSocketMonitor(config, discovery)
    print("   ✓ Monitor created")

    # Track how many updates we've received
    update_count = [0]  # Use list to allow modification in nested function

    async def on_trigger(ticker, yes_price, no_price):
        """Callback for triggered markets"""
        update_count[0] += 1
        print(f"\n   🎯 TRIGGER #{update_count[0]}: {ticker}")
        print(f"      YES={yes_price:.2f}¢ NO={no_price:.2f}¢")

        # Stop after 10 triggers
        if update_count[0] >= 10:
            print("\n✅ Received 10 triggers, test complete!")
            raise KeyboardInterrupt

    # Connect and listen
    print("\n3. Connecting to WebSocket...")
    await monitor.connect()

    print("\n4. Listening for price updates...")
    print("   (This will print when sports markets cross 90¢)")
    print("   Press Ctrl+C to stop\n")

    monitor.on_market_triggered = on_trigger

    try:
        await monitor.listen()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test stopped")

    print("\n" + "=" * 80)
    print("✅ WebSocket test complete")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
