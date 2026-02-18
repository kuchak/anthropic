"""
WebSocket Market Monitor - Using kalshi-python-unofficial library

This implementation uses the official kalshi-python-unofficial library's
WebSocket client, which has working authentication and streaming.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, Callable, Optional
from dateutil.parser import parse as parse_datetime

import websockets

import kalshi.websocket
import kalshi.auth

logger = logging.getLogger(__name__)


class KalshiWebSocketMonitor(kalshi.websocket.Client):
    """
    Real-time market monitor using kalshi-python-unofficial library.

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
        super().__init__()

        self.config = config
        self.series_discovery = series_discovery

        # Configure authentication (kalshi.auth IS the singleton Auth instance)
        kalshi.auth.set_key(
            access_key=config['kalshi_api_key_id'],
            private_key_path=config['kalshi_private_key_path']
        )

        # WebSocket URL (trading-api.kalshi.com is the current production endpoint)
        self.ws_url = "wss://trading-api.kalshi.com/trade-api/ws/v2"

        # Callbacks
        self.on_market_triggered_callback: Optional[Callable] = None

        # Market metadata cache (ticker -> market_data)
        self.market_metadata: Dict[str, Dict] = {}
        self.last_metadata_refresh = None

        # Track which markets we've already triggered on
        self.triggered_tickers: Set[str] = set()

        # Connection state
        self.connected = False

        logger.info("Kalshi WebSocket monitor initialized (using official library)")

    async def connect(self, url=None):
        """
        Override parent connect to fix extra_headers -> additional_headers
        incompatibility with websockets 12+.

        The kalshi-python-unofficial library uses extra_headers which was
        removed in websockets 12+. This override uses additional_headers.
        """
        if url is None:
            url = self.ws_url

        logger.info("Connecting to WebSocket: %s", url)
        async with websockets.connect(
            url,
            additional_headers=kalshi.auth.request_headers("GET", url),
        ) as ws:
            self.ws = ws
            logger.info("Connected to WebSocket: %s", url)
            await self.on_open()
            await self.handler()

    async def on_open(self):
        """Called when WebSocket connection is opened"""
        logger.info("✅ WebSocket connected")
        self.connected = True

        # Subscribe to ticker channel
        await self.subscribe(["ticker"])
        logger.info("📡 Subscribed to ticker channel (all markets)")

    async def on_message(self, message: dict):
        """
        Handle incoming messages from WebSocket.

        Args:
            message: Message dict from WebSocket
        """
        msg_type = message.get('type')

        if msg_type == 'ticker':
            await self._handle_ticker_update(message)

    async def on_error(self, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.connected = False

    async def on_close(self, close_status_code, close_msg):
        """Handle WebSocket closure"""
        logger.warning(f"WebSocket closed: code={close_status_code}, msg={close_msg}")
        self.connected = False

    def _is_sports_market(self, ticker: str) -> bool:
        """
        Check if ticker is a sports market using discovery cache.

        Args:
            ticker: Market ticker

        Returns:
            True if sports market
        """
        series = ticker.split('-')[0] if '-' in ticker else ticker
        sports_series = self.series_discovery.get_sports_series()
        return series in sports_series

    def _should_trigger(self, ticker: str, yes_bid: float, yes_ask: float) -> bool:
        """
        Check if market meets trigger criteria.

        Criteria:
        - Price >= 90¢ (either yes_ask or no_ask)
        - Sports market
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
        no_price = 1.0 - (yes_bid / 100.0)

        # Check price threshold (90¢)
        if yes_price < 0.90 and no_price < 0.90:
            return False

        # Check if sports market
        if not self._is_sports_market(ticker):
            return False

        # Check expiration time
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
        """
        Handle ticker update message.

        Args:
            msg: Ticker message
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
                if self.on_market_triggered_callback:
                    await self.on_market_triggered_callback(ticker, yes_price, no_price)

        except Exception as e:
            logger.debug(f"Error handling ticker update: {e}")

    async def _refresh_metadata_loop(self):
        """
        Background task to refresh market metadata every 5 minutes.
        """
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

                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in metadata refresh: {e}")
                await asyncio.sleep(60)

    async def run_monitor(self, on_market_triggered: Callable):
        """
        Run WebSocket monitor with reconnection logic.

        Args:
            on_market_triggered: Async callback(ticker, yes_price, no_price)
        """
        self.on_market_triggered_callback = on_market_triggered

        while True:
            try:
                # Start metadata refresh in background
                metadata_task = asyncio.create_task(self._refresh_metadata_loop())

                # Connect and run
                await self.connect(self.ws_url)

                # Cancel metadata task when connection closes
                metadata_task.cancel()

            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    def reset_trigger(self, ticker: str):
        """
        Reset trigger state for a ticker.

        Args:
            ticker: Market ticker
        """
        if ticker in self.triggered_tickers:
            self.triggered_tickers.remove(ticker)
            logger.debug(f"Reset trigger for {ticker}")
