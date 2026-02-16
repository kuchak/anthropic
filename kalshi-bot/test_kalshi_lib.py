"""
Test using the official kalshi-python library
"""

import asyncio
from kalshi_python import KalshiClient, Environment


async def test_ticker():
    """Test connecting to ticker channel using kalshi-python library"""

    print("=" * 80)
    print("TESTING WITH KALSHI-PYTHON LIBRARY")
    print("=" * 80)

    print("\n1. Creating client...")

    # Create client without authentication (for public data)
    client = KalshiClient(environment=Environment.PROD)

    print("   ✅ Client created")

    print("\n2. Attempting to connect to WebSocket...")

    try:
        # Try connecting to WebSocket
        async with client.websocket() as ws:
            print("   ✅ Connected!")

            print("\n3. Subscribing to ticker channel...")

            # Subscribe to ticker for all markets
            await ws.subscribe(channels=["ticker"])

            print("   ✅ Subscribed")

            print("\n4. Waiting for messages (10 seconds)...")

            count = 0
            timeout_time = asyncio.get_event_loop().time() + 10

            while asyncio.get_event_loop().time() < timeout_time and count < 10:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                    count += 1
                    print(f"   #{count}: {msg}")

                except asyncio.TimeoutError:
                    continue

            print(f"\n✅ Received {count} messages")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ticker())
