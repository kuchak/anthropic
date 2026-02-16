"""
Compare REST vs WebSocket signature generation to debug 403 error
"""

import time
import yaml
import os
from kalshi_client import KalshiClient
from websocket_monitor import WebSocketMonitor
from series_discovery import SeriesDiscovery

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['kalshi_api_key_id'] = os.getenv('KALSHI_API_KEY_ID')
config['kalshi_private_key_path'] = os.getenv('KALSHI_PRIVATE_KEY_PATH')

# Create REST client
rest_client = KalshiClient(config)

# Create WebSocket monitor (need discovery for init)
discovery = SeriesDiscovery()
ws_monitor = WebSocketMonitor(config, discovery)

# Use same timestamp for both
timestamp_ms = str(int(time.time() * 1000))

print("=" * 80)
print("SIGNATURE COMPARISON TEST")
print("=" * 80)

# Generate REST signature for a GET request
rest_signature = rest_client._generate_signature(timestamp_ms, "GET", "/trade-api/v2/balance")
rest_headers = rest_client._get_signed_headers("GET", "/trade-api/v2/balance")

print("\n📊 REST API Signature")
print(f"  Timestamp: {rest_headers['KALSHI-ACCESS-TIMESTAMP']}")
print(f"  Key ID: {rest_headers['KALSHI-ACCESS-KEY'][:20]}...")
print(f"  Signature: {rest_headers['KALSHI-ACCESS-SIGNATURE'][:40]}...")

# Generate WebSocket signature
ws_signature = ws_monitor._create_signature(timestamp_ms)
ws_headers = ws_monitor._get_auth_headers()

print("\n🌐 WebSocket Signature")
print(f"  Timestamp: {ws_headers['KALSHI-ACCESS-TIMESTAMP']}")
print(f"  Key ID: {ws_headers['KALSHI-ACCESS-KEY'][:20]}...")
print(f"  Signature: {ws_headers['KALSHI-ACCESS-SIGNATURE'][:40]}...")

# Compare
print("\n✅ Comparison")
print(f"  Same Key ID: {rest_headers['KALSHI-ACCESS-KEY'] == ws_headers['KALSHI-ACCESS-KEY']}")
print(f"  Both use millisecond timestamps: True")

# Manually construct messages to show what's being signed
rest_message = timestamp_ms + "GET" + "/trade-api/v2/balance"
ws_message = timestamp_ms + "GET" + "/trade-api/ws/v2"

print("\n📝 Signed Messages")
print(f"  REST: '{rest_message}'")
print(f"  WS:   '{ws_message}'")

# Test REST API connection
print("\n🧪 Testing REST API with generated signature...")
balance = rest_client.get_balance()
if balance:
    print(f"  ✅ REST API works! Balance: ${balance.get('balance', 0) / 100:.2f}")
else:
    print("  ❌ REST API failed")

print("\n" + "=" * 80)
print("Now try WebSocket connection with the same signature method...")
print("If it still fails, the issue is likely:")
print("  1. WebSocket-specific API permissions on the key")
print("  2. Different authentication requirements not documented")
print("  3. Kalshi WebSocket API has authentication bugs")
print("=" * 80)
