# WebSocket Connection Investigation

## Issue
WebSocket connection to Kalshi API fails with HTTP 403 error.

## Findings

### Authentication Required
Contrary to some third-party documentation, Kalshi's WebSocket API **requires authentication** even for public channels like `ticker`. This was confirmed by:
1. Official Kalshi docs stating "Authentication is required to establish the connection"
2. Testing multiple URLs without auth - all returned 403
3. The official documentation is clear despite some confusion from third-party sources

### URLs Tested
All of the following URLs returned HTTP 403 without authentication:
- `wss://api.elections.kalshi.com/trade-api/ws/v2` (currently used)
- `wss://trading-api.kalshi.com/trade-api/v2/ws` (alternative production)
- `wss://demo-api.kalshi.co/trade-api/v2/ws` (demo environment)

### Authentication Implementation
Our current implementation:
1. **REST API authentication**: ✅ WORKS
   - Successfully connects and retrieves data
   - Uses RSA-PSS signature with DIGEST_LENGTH salt
   - Message format: `timestamp + method + path`

2. **WebSocket authentication**: ❌ FAILS (HTTP 403)
   - Uses identical signature method to REST API
   - Same private key and API key ID
   - Message format: `timestamp + "GET" + "/trade-api/ws/v2"`
   - Headers: KALSHI-ACCESS-KEY, KALSHI-ACCESS-SIGNATURE, KALSHI-ACCESS-TIMESTAMP

### Signature Method
Both REST and WebSocket use:
```python
signature = private_key.sign(
    message.encode('utf-8'),
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.DIGEST_LENGTH  # Changed from MAX_LENGTH
    ),
    hashes.SHA256()
)
```

## Current Status
- REST API: Working correctly
- WebSocket: 403 error with authentication
- Root cause: Unknown - authentication method appears correct but is being rejected

## Next Steps
1. Check if there are additional WebSocket-specific authentication requirements
2. Verify the exact message format for WebSocket signatures
3. Check if API key has WebSocket permissions
4. Consider reaching out to Kalshi support for WebSocket authentication guidance
5. Look for working open-source examples of Kalshi WebSocket connections

## Test Files Created
- `test_ws_simple.py`: Simple WebSocket test without auth
- `test_ws_urls.py`: Test multiple WebSocket URLs
- `test_kalshi_lib.py`: Test using kalshi-python library
- `quick_api_test.py`: Test REST API authentication

## References
- [Kalshi WebSocket Docs](https://docs.kalshi.com/websockets/websocket-connection)
- [Kalshi Quick Start](https://docs.kalshi.com/getting_started/quick_start_websockets)
- [RoundProxies Guide](https://roundproxies.com/blog/scrape-kalshi/) (Feb 2026)
- [Unofficial Python Client](https://github.com/humz2k/kalshi-python-unofficial)
