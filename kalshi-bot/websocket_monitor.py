"""
WebSocket Market Monitor

Connects to Kalshi WebSocket API and streams real-time price updates.
Filters for sports markets crossing 90¢ threshold and expiring within 3 hours.
Replaces polling 434+ series every 30 seconds with a single WebSocket connection.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, Callable, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import websockets
from dateutil.parser import parse as parse_datetime

logger = logging.getLogger(__name__)


class WebSocketMonitor:
    """
    Real-time market monitor using WebSocket streaming.

    Subscribes to ticker channel and filters for relevant sports markets.
    Triggers callback when markets cross 90¢ threshold.
    """

    def __init__(self, config: Dict, series_discovery):
        """
        Initialize WebSocket monitor.

        Args:
            config: Bot configuration with API credentials
            series_discovery: SeriesDiscovery instance for checking if ticker is sports
        """
        self.config = config
        self.series_discovery = series_discovery

        # WebSocket connection
        self.ws_url = "wss://trading-api.kalshi.com/trade-api/ws/v2"
        self.ws = None
        self.connected = False

        # Authentication
        self.api_key_id = config['kalshi_api_key_id']
        self.private_key_path = config['kalshi_private_key_path']
        self.private_key = None

        # Callbacks
        self.on_market_triggered: Optional[Callable] = None

        # Market metadata cache (ticker -> market_data)
        # We need to fetch this occasionally to know expiration times
        self.market_metadata: Dict[str, Dict] = {}
        self.last_metadata_refresh = None

        # Track which markets we've already triggered on (to avoid spam)
        self.triggered_tickers: Set[str] = set()

        # Load private key
        self._load_private_key()

        logger.info("WebSocket monitor initialized")

    def _load_private_key(self):
        """Load RSA private key for authentication"""
        try:
            with open(self.private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.debug("Private key loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise

    def _create_signature(self, timestamp_ms: str) -> str:
        """
        Create RSA-PSS signature for WebSocket authentication.

        Args:
            timestamp_ms: Unix timestamp in milliseconds (as string)

        Returns:
            Base64-encoded signature
        """
        # Message format: timestamp + method + path (exactly like REST API)
        # Use string concatenation, not f-string
        message = timestamp_ms + "GET" + "/trade-api/ws/v2"

        # Sign with RSA-PSS (using digest-length salt as per Kalshi docs)
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )

        # Base64 encode
        import base64
        return base64.b64encode(signature).decode('utf-8')

    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for WebSocket connection"""
        # Create timestamp as STRING (exactly like REST API)
        timestamp_ms = str(int(time.time() * 1000))
        signature = self._create_signature(timestamp_ms)

        return {
            'KALSHI-ACCESS-KEY': self.api_key_id,
            'KALSHI-ACCESS-SIGNATURE': signature,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_ms
        }

    async def connect(self):
        """Establish WebSocket connection with authentication"""
        try:
            auth_headers = self._get_auth_headers()

            # Log full details for debugging
            timestamp_ms = auth_headers['KALSHI-ACCESS-TIMESTAMP']
            message = timestamp_ms + "GET" + "/trade-api/ws/v2"

            logger.info(f"Connecting to {self.ws_url}...")
            print(f"\n🔍 DEBUG: WebSocket Authentication Details")
            print(f"  URL: {self.ws_url}")
            print(f"  Timestamp: {timestamp_ms}")
            print(f"  Signed message: '{message}'")
            print(f"  Headers:")
            for key, value in auth_headers.items():
                if len(value) > 50:
                    print(f"    {key}: {value[:50]}...")
                else:
                    print(f"    {key}: {value}")

            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers=auth_headers,
                ping_interval=20,
                ping_timeout=10
            )

            self.connected = True
            logger.info("✅ WebSocket connected")

            # Subscribe to ticker channel
            await self._subscribe_ticker()

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.connected = False
            raise

    async def _subscribe_ticker(self):
        """Subscribe to ticker channel for all market price updates"""
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }

        await self.ws.send(json.dumps(subscribe_msg))
        logger.info("📡 Subscribed to ticker channel (all markets)")

    async def _fetch_market_metadata(self, ticker: str) -> Optional[Dict]:
        """
        Fetch market metadata from REST API to get expiration time.

        Args:
            ticker: Market ticker

        Returns:
            Market data dict or None
        """
        try:
            from kalshi_client import KalshiClient
            client = KalshiClient(self.config)
            market_data = client.get_market(ticker)
            return market_data
        except Exception as e:
            logger.debug(f"Failed to fetch metadata for {ticker}: {e}")
            return None

    def _is_sports_market(self, ticker: str) -> bool:
        """
        Check if ticker is a sports market using discovery cache.

        Args:
            ticker: Market ticker (e.g., KXNCAAMBGAME-26FEB16DUKUNC-DUKE)

        Returns:
            True if sports market
        """
        # Extract series ticker (first part before hyphen)
        series = ticker.split('-')[0] if '-' in ticker else ticker

        # Check if in sports series list
        sports_series = self.series_discovery.get_sports_series()
        return series in sports_series

    def _should_trigger(self, ticker: str, yes_bid: float, yes_ask: float) -> bool:
        """
        Check if market meets trigger criteria.

        Criteria:
        - Price >= 90¢ (either yes_ask or no_ask)
        - Sports market (from discovery)
        - Expires within 3 hours
        - Not already triggered

        Args:
            ticker: Market ticker
            yes_bid: Yes bid price in cents
            yes_ask: Yes ask price in cents

        Returns:
            True if should trigger
        """
        # Already triggered?
        if ticker in self.triggered_tickers:
            return False

        # Convert to dollars
        yes_price = yes_ask / 100.0
        no_price = 1.0 - (yes_bid / 100.0)  # Approximate no_ask

        # Check price threshold (90¢)
        if yes_price < 0.90 and no_price < 0.90:
            return False

        # Check if sports market
        if not self._is_sports_market(ticker):
            return False

        # Check expiration time (need metadata)
        if ticker not in self.market_metadata:
            # Metadata not cached, skip for now
            # It will be fetched in background task
            return False

        market_data = self.market_metadata[ticker]
        exp_time_str = market_data.get('expected_expiration_time')

        if not exp_time_str:
            return False

        try:
            exp_time = parse_datetime(exp_time_str)
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=3)

            # Must expire within 3 hours
            if not (now < exp_time <= cutoff):
                return False

        except Exception as e:
            logger.debug(f"Failed to parse expiration for {ticker}: {e}")
            return False

        # All criteria met!
        return True

    async def _handle_ticker_update(self, msg: Dict):
        """
        Handle ticker update message.

        Args:
            msg: Ticker message from WebSocket
        """
        try:
            ticker = msg.get('market_ticker')
            yes_bid = msg.get('yes_bid', 0)
            yes_ask = msg.get('yes_ask', 0)

            if not ticker:
                return

            # Check if should trigger
            if self._should_trigger(ticker, yes_bid, yes_ask):
                yes_price = yes_ask / 100.0
                no_price = 1.0 - (yes_bid / 100.0)

                logger.info(f"🎯 TRIGGER: {ticker} | YES={yes_price:.2f}¢ NO={no_price:.2f}¢")

                # Mark as triggered
                self.triggered_tickers.add(ticker)

                # Call callback
                if self.on_market_triggered:
                    await self.on_market_triggered(ticker, yes_price, no_price)

        except Exception as e:
            logger.debug(f"Error handling ticker update: {e}")

    async def _refresh_metadata_loop(self):
        """
        Background task to refresh market metadata every 5 minutes.

        Fetches metadata for all active sports markets to check expiration times.
        """
        while self.connected:
            try:
                logger.debug("Refreshing market metadata...")

                # Get all sports series
                sports_series = self.series_discovery.get_sports_series()

                # Fetch markets for each series (limited to active markets)
                from kalshi_client import KalshiClient
                client = KalshiClient(self.config)

                new_metadata = {}
                for series in sports_series[:50]:  # Limit to avoid rate limits
                    try:
                        markets = client.get_markets(
                            category=series,
                            status='active',
                            limit=100
                        )

                        for market in markets:
                            ticker = market.get('ticker')
                            if ticker:
                                new_metadata[ticker] = market

                        await asyncio.sleep(0.1)  # Rate limiting

                    except Exception as e:
                        logger.debug(f"Error fetching {series}: {e}")
                        continue

                self.market_metadata = new_metadata
                self.last_metadata_refresh = datetime.now(timezone.utc)

                logger.debug(f"Metadata refreshed: {len(new_metadata)} markets")

                # Wait 5 minutes before next refresh
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in metadata refresh: {e}")
                await asyncio.sleep(60)

    async def listen(self):
        """
        Main listening loop for WebSocket messages.

        Processes ticker updates and triggers callbacks.
        """
        logger.info("🎧 Listening for price updates...")

        # Start metadata refresh task
        metadata_task = asyncio.create_task(self._refresh_metadata_loop())

        try:
            async for message in self.ws:
                try:
                    msg = json.loads(message)
                    msg_type = msg.get('type')

                    if msg_type == 'ticker':
                        await self._handle_ticker_update(msg)

                except json.JSONDecodeError:
                    logger.debug(f"Invalid JSON: {message}")
                except Exception as e:
                    logger.debug(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            self.connected = False
        finally:
            metadata_task.cancel()

    async def run(self, on_market_triggered: Callable):
        """
        Run WebSocket monitor.

        Args:
            on_market_triggered: Async callback function(ticker, yes_price, no_price)
        """
        self.on_market_triggered = on_market_triggered

        while True:
            try:
                await self.connect()
                await self.listen()

            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    def reset_trigger(self, ticker: str):
        """
        Reset trigger state for a ticker.

        Call this after processing a market so it can trigger again if needed.

        Args:
            ticker: Market ticker
        """
        if ticker in self.triggered_tickers:
            self.triggered_tickers.remove(ticker)
            logger.debug(f"Reset trigger for {ticker}")
