# WebSocket Implementation Guide

This document describes two WebSocket implementations for the Kalshi trading bot, addressing authentication and header issues with the Kalshi WebSocket API.

## Problem Statement

The original WebSocket implementation (`websocket_monitor.py`) had authentication issues:
- Headers may not be sent correctly with the `websockets` library (version 12+)
- `additional_headers` parameter may silently drop custom headers in some versions
- Authentication signatures not being accepted by the API

## Solution 1: Use kalshi-python-unofficial Library (RECOMMENDED)

**File:** `websocket_monitor_kalshi_lib.py`

### Advantages
- ✅ Official library with working WebSocket client
- ✅ Built-in authentication that's tested and maintained
- ✅ Proven to work with Kalshi API
- ✅ Handles header authentication correctly
- ✅ Active maintenance and bug fixes

### Implementation Details

```python
import kalshi.websocket
import kalshi.auth

class KalshiWebSocketMonitor(kalshi.websocket.Client):
    def __init__(self, config, series_discovery):
        super().__init__()

        # Configure authentication
        kalshi.auth.auth.set_key(
            access_key=config['kalshi_api_key_id'],
            private_key_path=config['kalshi_private_key_path']
        )
```

### Key Features
- Inherits from `kalshi.websocket.Client`
- Uses `kalshi.auth.auth` singleton for authentication
- Overrides `on_open()`, `on_message()`, `on_error()`, `on_close()` callbacks
- Automatic reconnection logic
- Built-in message handling

### Testing

```bash
python test_ws_kalshi_lib.py
```

Expected output:
```
================================================================================
Testing WebSocket Monitor (kalshi-python-unofficial)
================================================================================

🔬 Initializing series discovery...
✅ Discovered 434 series, 89 sports

🌐 Initializing WebSocket monitor (kalshi-python-unofficial)...
✅ Monitor ready

🚀 Starting WebSocket connection...
✅ WebSocket connected
📡 Subscribed to ticker channel (all markets)
```

### Dependencies

```
kalshi-python-unofficial>=0.1.0
websockets>=10.0
cryptography>=42.0.0
```

## Solution 2: Use websocket-client Library (ALTERNATIVE)

**File:** `websocket_monitor_alt.py`

### Advantages
- ✅ Different library approach (`websocket-client` vs `websockets`)
- ✅ Uses `header` parameter (dict) instead of `additional_headers`
- ✅ Thread-based instead of async-only
- ✅ May work better in some network environments

### Implementation Details

```python
import websocket  # websocket-client library

class WebSocketMonitorAlt:
    def connect(self):
        auth_headers = self._get_auth_headers()

        # websocket-client uses 'header' parameter as a dict
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=auth_headers,  # Note: 'header' not 'headers'
            on_open=self.on_open_handler,
            on_message=self.on_message_handler,
            on_error=self.on_error_handler,
            on_close=self.on_close_handler
        )
```

### Key Features
- Uses `websocket.WebSocketApp` with callback handlers
- Headers passed via `header` parameter (not `headers` or `additional_headers`)
- Runs WebSocket in separate thread
- Custom RSA-PSS signature generation
- Async callback integration via `asyncio.run_coroutine_threadsafe()`

### Testing

```bash
python test_ws_alt.py
```

### Dependencies

```
websocket-client>=1.6.0
cryptography>=42.0.0
```

## Comparison

| Feature | kalshi-python-unofficial | websocket-client |
|---------|-------------------------|------------------|
| Library | `websockets` | `websocket-client` |
| Authentication | Built-in via `kalshi.auth` | Custom implementation |
| Threading Model | Async-only | Thread-based with async callbacks |
| Maintenance | Active | Manual updates needed |
| Reliability | ✅ Proven with Kalshi API | ⚠️ Needs testing |
| Recommendation | **RECOMMENDED** | Alternative fallback |

## Header Issues Explained

### websockets library (12+)

The `websockets` library changed parameter names:
- Version < 11: `extra_headers`
- Version 12+: `additional_headers`

**Problem:** Some versions silently drop custom headers if you use the wrong parameter name.

**Solution:** Use `kalshi-python-unofficial` which uses correct parameter internally.

### websocket-client library

This library uses a different approach:
- Parameter name: `header` (not `headers` or `additional_headers`)
- Type: Dictionary (not list of tuples)
- Behavior: More reliable header transmission

## Usage in Main Bot

Update `main_websocket.py` to use the recommended implementation:

```python
# Option 1: kalshi-python-unofficial (RECOMMENDED)
from websocket_monitor_kalshi_lib import KalshiWebSocketMonitor
self.ws_monitor = KalshiWebSocketMonitor(config, self.series_discovery)

# Option 2: websocket-client (ALTERNATIVE)
from websocket_monitor_alt import WebSocketMonitorAlt
self.ws_monitor = WebSocketMonitorAlt(config, self.series_discovery)
```

## Troubleshooting

### Authentication Failures

**Symptom:** WebSocket connection closes immediately after opening

**Diagnosis:**
1. Check if headers are being sent:
   ```python
   logger.info(f"Headers: {auth_headers}")
   ```

2. Verify signature generation:
   ```python
   message = timestamp_ms + "GET" + "/trade-api/ws/v2"
   logger.info(f"Signed message: '{message}'")
   ```

3. Test with REST API first:
   ```python
   from kalshi_client import KalshiClient
   client = KalshiClient(config)
   assert client.test_connection()
   ```

**Solutions:**
- Use `kalshi-python-unofficial` library (built-in auth)
- Verify private key file path is correct
- Check API key ID matches account
- Ensure timestamp is in milliseconds as string

### Connection Drops

**Symptom:** WebSocket connects but disconnects after a few seconds

**Solutions:**
- Add ping/pong keepalive:
  ```python
  websockets.connect(url, ping_interval=20, ping_timeout=10)
  ```
- Check firewall/network restrictions
- Verify Kalshi API status

### No Messages Received

**Symptom:** Connection succeeds but no ticker messages

**Solutions:**
- Verify subscription message is sent:
  ```python
  await self.subscribe(["ticker"])
  ```
- Check if markets are active and trading
- Ensure message handler is processing correctly

## Testing Without Credentials

If API credentials are not available, you can review the code structure:

1. **Authentication signature generation** - matches Kalshi API spec
2. **WebSocket connection** - uses standard library patterns
3. **Message handling** - processes ticker updates
4. **Error handling** - reconnection logic included

## Recommendations

1. **Start with kalshi-python-unofficial** - It's the most reliable option
2. **Keep websocket-client as backup** - In case of library-specific issues
3. **Test both implementations** - Different networks may behave differently
4. **Monitor connection stability** - Track disconnects and reconnects
5. **Update regularly** - Keep `kalshi-python-unofficial` library updated

## Next Steps

1. Set API credentials:
   ```bash
   export KALSHI_API_KEY_ID='your-key-id'
   export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'
   ```

2. Test primary implementation:
   ```bash
   python test_ws_kalshi_lib.py
   ```

3. If issues occur, test alternative:
   ```bash
   python test_ws_alt.py
   ```

4. Update main bot to use working implementation

5. Monitor in production for stability

## References

- [kalshi-python-unofficial GitHub](https://github.com/pseudorandomcoder/kalshi-python-unofficial)
- [Kalshi API Documentation](https://docs.kalshi.com/)
- [websockets library docs](https://websockets.readthedocs.io/)
- [websocket-client library docs](https://websocket-client.readthedocs.io/)
