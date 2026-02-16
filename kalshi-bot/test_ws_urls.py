"""
Test different WebSocket URLs to find the correct endpoint
"""

import asyncio
import json
import websockets


async def try_url(ws_url):
    """Try connecting to a specific WebSocket URL"""

    print(f"\n{'='*80}")
    print(f"Testing: {ws_url}")
    print('='*80)

    try:
        # Connect WITHOUT authentication
        ws = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=10
        )

        print("✅ Connected!")

        # Subscribe to ticker channel
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }

        await ws.send(json.dumps(subscribe_msg))
        print("✅ Subscription sent")

        # Wait for one message
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"✅ Received message: {data.get('type', 'unknown')}")
            await ws.close()
            return True

        except asyncio.TimeoutError:
            print("⚠️  No messages received (timeout)")
            await ws.close()
            return False

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def main():
    """Test multiple WebSocket URLs"""

    print("=" * 80)
    print("TESTING KALSHI WEBSOCKET URLS")
    print("=" * 80)

    urls = [
        "wss://api.elections.kalshi.com/trade-api/ws/v2",
        "wss://trading-api.kalshi.com/trade-api/v2/ws",
        "wss://demo-api.kalshi.co/trade-api/v2/ws",
    ]

    for url in urls:
        success = await try_url(url)
        if success:
            print(f"\n🎉 SUCCESS with: {url}")
            return

    print("\n❌ All URLs failed")


if __name__ == "__main__":
    asyncio.run(main())
