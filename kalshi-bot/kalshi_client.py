"""
Kalshi API Client
Handles API key authentication with RSA signing, rate limiting, retries, and all API interactions
"""
import os
import time
import base64
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from dateutil.parser import parse as parse_datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from logger_setup import get_logger
from models import Market

logger = get_logger("kalshi_client")


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, requests_per_second: float):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait_if_needed(self):
        """Sleep if necessary to respect rate limit"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()


class KalshiClient:
    """
    Kalshi API v2 client with RSA API key authentication, rate limiting, and retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config['kalshi_api_base']

        # API Key authentication
        self.api_key_id = os.getenv('KALSHI_API_KEY_ID')
        private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

        if not self.api_key_id or not private_key_path:
            raise ValueError(
                "KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH environment variables must be set\n"
                "Get your API keys at: https://kalshi.com/account/profile\n"
                "Or use demo: https://demo.kalshi.com/account/profile"
            )

        # Load private key
        try:
            with open(private_key_path, 'rb') as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info(f"✅ Loaded private key from {private_key_path}")
        except Exception as e:
            raise ValueError(f"Failed to load private key: {e}")

        self.session = requests.Session()

        # Rate limiting
        self.rate_limiter = RateLimiter(config['api_requests_per_second'])

        # Retry config
        self.max_retries = config['retry_max_attempts']
        self.retry_backoff = config['retry_backoff_seconds']

        logger.info(f"Kalshi client initialized. Base URL: {self.base_url}")
        logger.info(f"API Key ID: {self.api_key_id}")

    def _generate_signature(self, timestamp_ms: str, method: str, path: str) -> str:
        """
        Generate RSA-PSS signature for API request

        Args:
            timestamp_ms: Request timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            path: API path WITHOUT query parameters

        Returns:
            Base64-encoded signature
        """
        # Message to sign: timestamp + method + path
        message = timestamp_ms + method + path
        message_bytes = message.encode('utf-8')

        # Sign with RSA-PSS
        signature = self.private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )

        # Encode to base64
        return base64.b64encode(signature).decode('utf-8')

    def _get_signed_headers(self, method: str, path: str) -> Dict[str, str]:
        """
        Generate signed authentication headers

        Args:
            method: HTTP method
            path: API path WITHOUT query parameters

        Returns:
            Dictionary of authentication headers
        """
        # Timestamp in milliseconds
        timestamp_ms = str(int(time.time() * 1000))

        # Generate signature
        signature = self._generate_signature(timestamp_ms, method, path)

        return {
            'KALSHI-ACCESS-KEY': self.api_key_id,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_ms,
            'KALSHI-ACCESS-SIGNATURE': signature,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting and retry logic

        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., '/markets')
            params: Query parameters
            json_data: JSON body for POST requests
            retry_count: Current retry attempt

        Returns:
            Response JSON
        """
        self.rate_limiter.wait_if_needed()

        # Full path for signing (without query params)
        path = endpoint
        if not path.startswith('/trade-api/v2'):
            path = f"/trade-api/v2{endpoint}"

        # Generate signed headers
        headers = self._get_signed_headers(method, path)

        # Full URL
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=json_data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** retry_count)
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._request(method, endpoint, params, json_data, retry_count + 1)
                else:
                    raise Exception("Max retries exceeded for rate limit")

            # Handle server errors
            if response.status_code >= 500:
                if retry_count < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** retry_count)
                    logger.warning(f"Server error ({response.status_code}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._request(method, endpoint, params, json_data, retry_count + 1)
                else:
                    raise Exception(f"Max retries exceeded. Last status: {response.status_code}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_backoff * (2 ** retry_count)
                logger.warning(f"Request failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._request(method, endpoint, params, json_data, retry_count + 1)
            else:
                logger.error(f"Request failed after {self.max_retries} retries: {e}")
                raise

    def test_connection(self) -> bool:
        """
        Test API connection and authentication

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Testing API connection and authentication...")
            response = self._request('GET', '/exchange/status')
            if response.get('exchange_active'):
                logger.info("✅ API connection and authentication successful")
                return True
            else:
                logger.warning("⚠️  API connected but exchange not active")
                return False
        except Exception as e:
            logger.error(f"❌ API connection failed: {e}")
            return False

    def get_markets(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 1000,
        max_total: Optional[int] = None,
        min_volume: Optional[int] = None,
        max_expected_expiration_time: Optional[str] = None,
        is_live: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of markets with optional filters (with automatic pagination)

        Args:
            status: Filter by status (e.g., 'open', 'closed', 'settled')
            category: Filter by series ticker
            limit: Number of markets per page (max 1000)
            max_total: Maximum total markets to fetch across all pages (None = fetch all)
            min_volume: Minimum 24h volume (server-side filter)
            max_expected_expiration_time: ISO timestamp for max expected expiration (e.g., '2026-02-13T15:00:00Z')
            is_live: Filter for live markets (e.g., 'true')

        Returns:
            List of market dictionaries
        """
        all_markets = []
        cursor = None
        page = 0

        while True:
            page += 1
            params = {'limit': limit}
            if status:
                params['status'] = status
            if category:
                params['series_ticker'] = category
            if min_volume is not None:
                params['min_volume'] = min_volume
            if max_expected_expiration_time:
                params['max_expected_expiration_time'] = max_expected_expiration_time
            if is_live:
                params['is_live'] = is_live
            if cursor:
                params['cursor'] = cursor

            try:
                response = self._request('GET', '/markets', params=params)
                markets = response.get('markets', [])
                all_markets.extend(markets)

                logger.debug(f"Page {page}: Retrieved {len(markets)} markets (total so far: {len(all_markets)})")

                # Check if we've hit max_total limit
                if max_total and len(all_markets) >= max_total:
                    all_markets = all_markets[:max_total]
                    logger.debug(f"Reached max_total limit of {max_total} markets")
                    break

                # Check if there's another page
                cursor = response.get('cursor')
                if not cursor or not markets:
                    logger.debug(f"No more pages. Total markets retrieved: {len(all_markets)}")
                    break

            except Exception as e:
                logger.error(f"Failed to get markets on page {page}: {e}")
                break

        return all_markets

    def get_market(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get single market details

        Args:
            ticker: Market ticker symbol

        Returns:
            Market dictionary or None if not found
        """
        try:
            response = self._request('GET', f'/markets/{ticker}')
            market = response.get('market')
            return market
        except Exception as e:
            logger.error(f"Failed to get market {ticker}: {e}")
            return None

    def get_orderbook(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get market orderbook with best bid/ask prices

        Args:
            ticker: Market ticker symbol

        Returns:
            Orderbook dictionary or None if failed
        """
        try:
            response = self._request('GET', f'/markets/{ticker}/orderbook')
            return response.get('orderbook', {})
        except Exception as e:
            logger.error(f"Failed to get orderbook for {ticker}: {e}")
            return None

    def parse_market(self, market_data: Dict[str, Any]) -> Optional[Market]:
        """
        Parse API market data into Market object

        Args:
            market_data: Raw market data from API

        Returns:
            Market object or None if parsing fails
        """
        try:
            # Get orderbook for current prices
            orderbook = self.get_orderbook(market_data['ticker'])
            if not orderbook:
                return None

            yes_orders = orderbook.get('yes', [])
            no_orders = orderbook.get('no', [])

            # Best yes price is lowest ask
            best_yes_price = min([o['price'] / 100.0 for o in yes_orders], default=0.0)
            best_yes_size = sum([o['size'] for o in yes_orders if o['price'] / 100.0 == best_yes_price], default=0)

            # Best no price is lowest ask
            best_no_price = min([o['price'] / 100.0 for o in no_orders], default=0.0)
            best_no_size = sum([o['size'] for o in no_orders if o['price'] / 100.0 == best_no_price], default=0)

            return Market(
                ticker=market_data['ticker'],
                title=market_data['title'],
                category=market_data.get('series_ticker', 'unknown'),
                settlement_time=parse_datetime(market_data['close_time']),
                status=market_data['status'],
                best_yes_price=best_yes_price,
                best_no_price=best_no_price,
                best_yes_size=best_yes_size,
                best_no_size=best_no_size
            )

        except Exception as e:
            logger.error(f"Failed to parse market {market_data.get('ticker', 'unknown')}: {e}")
            return None

    def place_order(
        self,
        ticker: str,
        side: str,
        order_type: str,
        price: float,
        count: int
    ) -> Dict[str, Any]:
        """
        Place an order (only used when dry_run is False)

        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            order_type: 'market' or 'limit'
            price: Price in dollars (e.g., 0.92 for 92¢)
            count: Number of contracts

        Returns:
            Order response dictionary
        """
        price_cents = int(price * 100)

        payload = {
            'ticker': ticker,
            'action': 'buy',
            'side': side,
            'type': order_type,
            'yes_price': price_cents if side == 'yes' else None,
            'no_price': price_cents if side == 'no' else None,
            'count': count
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        logger.info(f"Placing order: {payload}")

        try:
            response = self._request('POST', '/portfolio/orders', json_data=payload)
            logger.info(f"✅ Order placed: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Failed to place order: {e}")
            raise

    def get_balance(self) -> Optional[float]:
        """
        Get current account balance

        Returns:
            Balance in dollars or None if failed
        """
        try:
            response = self._request('GET', '/portfolio/balance')
            balance_cents = response.get('balance', 0)
            return balance_cents / 100.0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return None

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current open positions

        Returns:
            List of position dictionaries
        """
        try:
            response = self._request('GET', '/portfolio/positions')
            return response.get('positions', [])
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
