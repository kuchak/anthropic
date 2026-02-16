"""
Simple WebSocket test - just connect and subscribe to ticker channel.
No authentication needed for public ticker channel.
"""

import asyncio
import json
import websockets


async def test_ticker():
    """Test connecting to ticker channel without authentication"""

    # Try different WebSocket URLs to find the correct one
    ws_urls = [
        "wss://api.elections.kalshi.com/trade-api/ws/v2",  # Current URL
        "wss://trading-api.kalshi.com/trade-api/v2/ws",     # Alternative from docs
        "wss://demo-api.kalshi.co/trade-api/v2/ws",         # Demo environment
    ]

    for ws_url in ws_urls:
        print(f"\nTrying: {ws_url}")
        if await try_connect(ws_url):
            print(f"\n✅ SUCCESS with: {ws_url}")
            return

    print("\n❌ All URLs failed")


async def try_connect(ws_url):
    """Try connecting to a specific WebSocket URL"""

    print("=" * 80)
    print("TESTING PUBLIC TICKER CHANNEL (NO AUTH)")
    print("=" * 80)

    print(f"\n1. Connecting to {ws_url}...")

    try:
        # Connect WITHOUT authentication headers, but with User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        ws = await websockets.connect(
            ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10
        )

        print("   ✅ Connected!")

        print("\n2. Subscribing to ticker channel...")

        # Subscribe to ticker channel
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }

        await ws.send(json.dumps(subscribe_msg))
        print("   ✅ Subscription sent")

        print("\n3. Waiting for messages (10 seconds)...")
        print("   (Showing first 10 ticker updates)\n")

        count = 0
        timeout = asyncio.create_task(asyncio.sleep(10))

        while count < 10:
            try:
                # Wait for message with timeout
                msg_task = asyncio.create_task(ws.recv())
                done, pending = await asyncio.wait(
                    {msg_task, timeout},
                    return_when=asyncio.FIRST_COMPLETED
                )

                if timeout in done:
                    print("\n   ⏱️  10 seconds elapsed")
                    break

                message = msg_task.result()
                data = json.loads(message)

                msg_type = data.get('type')

                if msg_type == 'ticker':
                    count += 1
                    ticker = data.get('market_ticker', 'unknown')
                    yes_bid = data.get('yes_bid', 0)
                    yes_ask = data.get('yes_ask', 0)

                    print(f"   #{count}: {ticker} | YES bid={yes_bid}¢ ask={yes_ask}¢")

                elif msg_type == 'subscribed':
                    print(f"   ✅ Subscription confirmed: {data}")
                else:
                    print(f"   📨 {msg_type}: {data}")

            except asyncio.TimeoutError:
                print("\n   ⏱️  Timeout waiting for messages")
                break
            except Exception as e:
                print(f"\n   ❌ Error receiving message: {e}")
                break

        await ws.close()

        print("\n" + "=" * 80)
        if count > 0:
            print(f"✅ SUCCESS! Received {count} ticker updates")
        else:
            print("⚠️  Connected but no ticker updates received")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n" + "=" * 80)
        print("FAILED")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ticker())
