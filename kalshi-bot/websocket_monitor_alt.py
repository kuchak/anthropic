"""
WebSocket Market Monitor - Alternative implementation using websocket-client

This implementation uses the websocket-client library (not websockets),
which handles headers differently and may have better compatibility.
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, Callable, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from dateutil.parser import parse as parse_datetime

import websocket  # websocket-client library

logger = logging.getLogger(__name__)


class WebSocketMonitorAlt:
    """
    Real-time market monitor using websocket-client library.

    Alternative implementation that uses websocket-client instead of websockets.
    This library handles headers via the header parameter as a dict.
    """

    def __init__(self, config: Dict, series_discovery):
        """
        Initialize WebSocket monitor.

        Args:
            config: Bot configuration with API credentials
            series_discovery: SeriesDiscovery instance
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

        # Market metadata cache
        self.market_metadata: Dict[str, Dict] = {}
        self.last_metadata_refresh = None

        # Track triggered markets
        self.triggered_tickers: Set[str] = set()

        # Event loop for async operations
        self.loop = None

        # Load private key
        self._load_private_key()

        logger.info("WebSocket monitor initialized (websocket-client library)")

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
        message = timestamp_ms + "GET" + "/trade-api/ws/v2"

        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )

        import base64
        return base64.b64encode(signature).decode('utf-8')

    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for WebSocket connection"""
        timestamp_ms = str(int(time.time() * 1000))
        signature = self._create_signature(timestamp_ms)

        return {
            'KALSHI-ACCESS-KEY': self.api_key_id,
            'KALSHI-ACCESS-SIGNATURE': signature,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_ms
        }

    def on_open_handler(self, ws):
        """Called when WebSocket connection is opened"""
        logger.info("✅ WebSocket connected")
        self.connected = True

        # Subscribe to ticker channel
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }

        ws.send(json.dumps(subscribe_msg))
        logger.info("📡 Subscribed to ticker channel (all markets)")

    def on_message_handler(self, ws, message):
        """
        Handle incoming WebSocket messages.

        Args:
            ws: WebSocket instance
            message: Raw message string
        """
        try:
            msg = json.loads(message)
            msg_type = msg.get('type')

            if msg_type == 'ticker':
                # Schedule async handler in event loop
                if self.loop and self.on_market_triggered:
                    asyncio.run_coroutine_threadsafe(
                        self._handle_ticker_update(msg),
                        self.loop
                    )

        except Exception as e:
            logger.debug(f"Error processing message: {e}")

    def on_error_handler(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.connected = False

    def on_close_handler(self, ws, close_status_code, close_msg):
        """Handle WebSocket closure"""
        logger.warning(f"WebSocket closed: code={close_status_code}, msg={close_msg}")
        self.connected = False

    def _is_sports_market(self, ticker: str) -> bool:
        """Check if ticker is a sports market"""
        series = ticker.split('-')[0] if '-' in ticker else ticker
        sports_series = self.series_discovery.get_sports_series()
        return series in sports_series

    def _should_trigger(self, ticker: str, yes_bid: float, yes_ask: float) -> bool:
        """Check if market meets trigger criteria"""
        if ticker in self.triggered_tickers:
            return False

        yes_price = yes_ask / 100.0
        no_price = 1.0 - (yes_bid / 100.0)

        if yes_price < 0.90 and no_price < 0.90:
            return False

        if not self._is_sports_market(ticker):
            return False

        if ticker not in self.market_metadata:
            return False

        market_data = self.market_metadata[ticker]
        exp_time_str = market_data.get('expected_expiration_time')

        if not exp_time_str:
            return False

        try:
            exp_time = parse_datetime(exp_time_str)
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=3)

            if not (now < exp_time <= cutoff):
                return False

        except Exception as e:
            logger.debug(f"Failed to parse expiration for {ticker}: {e}")
            return False

        return True

    async def _handle_ticker_update(self, msg: Dict):
        """Handle ticker update message"""
        try:
            ticker = msg.get('market_ticker')
            yes_bid = msg.get('yes_bid', 0)
            yes_ask = msg.get('yes_ask', 0)

            if not ticker:
                return

            if self._should_trigger(ticker, yes_bid, yes_ask):
                yes_price = yes_ask / 100.0
                no_price = 1.0 - (yes_bid / 100.0)

                logger.info(f"🎯 TRIGGER: {ticker} | YES={yes_price:.2f}¢ NO={no_price:.2f}¢")

                self.triggered_tickers.add(ticker)

                if self.on_market_triggered:
                    await self.on_market_triggered(ticker, yes_price, no_price)

        except Exception as e:
            logger.debug(f"Error handling ticker update: {e}")

    async def _refresh_metadata_loop(self):
        """Background task to refresh market metadata"""
        while self.connected:
            try:
                logger.debug("Refreshing market metadata...")

                sports_series = self.series_discovery.get_sports_series()

                from kalshi_client import KalshiClient
                client = KalshiClient(self.config)

                new_metadata = {}
                for series in sports_series[:50]:
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

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.debug(f"Error fetching {series}: {e}")
                        continue

                self.market_metadata = new_metadata
                self.last_metadata_refresh = datetime.now(timezone.utc)

                logger.debug(f"Metadata refreshed: {len(new_metadata)} markets")

                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in metadata refresh: {e}")
                await asyncio.sleep(60)

    def connect(self):
        """Establish WebSocket connection"""
        try:
            auth_headers = self._get_auth_headers()

            logger.info(f"Connecting to {self.ws_url}...")
            logger.debug(f"Auth headers: {list(auth_headers.keys())}")

            # websocket-client uses 'header' parameter as a dict
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                header=auth_headers,  # Note: header not headers, and dict not list
                on_open=self.on_open_handler,
                on_message=self.on_message_handler,
                on_error=self.on_error_handler,
                on_close=self.on_close_handler
            )

            # Run in separate thread
            ws_thread = threading.Thread(
                target=self.ws.run_forever,
                daemon=True
            )
            ws_thread.start()

            logger.info("WebSocket thread started")
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.connected = False
            return False

    async def run(self, on_market_triggered: Callable):
        """
        Run WebSocket monitor.

        Args:
            on_market_triggered: Async callback(ticker, yes_price, no_price)
        """
        self.on_market_triggered = on_market_triggered
        self.loop = asyncio.get_event_loop()

        # Start metadata refresh
        metadata_task = asyncio.create_task(self._refresh_metadata_loop())

        while True:
            try:
                if not self.connected:
                    self.connect()
                    await asyncio.sleep(3)  # Wait for connection

                # Keep running
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in run loop: {e}")
                await asyncio.sleep(5)

    def reset_trigger(self, ticker: str):
        """Reset trigger state for a ticker"""
        if ticker in self.triggered_tickers:
            self.triggered_tickers.remove(ticker)
            logger.debug(f"Reset trigger for {ticker}")
