"""
Kalshi API Client
Handles authentication, rate limiting, retries, and all API interactions
"""
import os
import time
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_datetime
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
    Kalshi API v2 client with authentication, rate limiting, and retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config['kalshi_api_base']
        self.email = os.getenv('KALSHI_EMAIL')
        self.password = os.getenv('KALSHI_PASSWORD')

        if not self.email or not self.password:
            raise ValueError("KALSHI_EMAIL and KALSHI_PASSWORD environment variables must be set")

        self.session = requests.Session()
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Rate limiting
        self.rate_limiter = RateLimiter(config['api_requests_per_second'])

        # Retry config
        self.max_retries = config['retry_max_attempts']
        self.retry_backoff = config['retry_backoff_seconds']

        logger.info(f"Kalshi client initialized. Base URL: {self.base_url}")

    def authenticate(self) -> bool:
        """
        Authenticate with Kalshi API and store auth token
        Returns True if successful, False otherwise
        """
        try:
            logger.info(f"Authenticating with Kalshi API as {self.email}")

            url = f"{self.base_url}/login"
            payload = {
                "email": self.email,
                "password": self.password
            }

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            self.token = data.get('token')

            if not self.token:
                logger.error("Authentication failed: No token in response")
                return False

            # Kalshi tokens typically expire in 24 hours
            self.token_expiry = datetime.utcnow() + timedelta(hours=23)

            # Set auth header for future requests
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })

            logger.info("✅ Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.token or not self.token_expiry:
            return False
        # Refresh if less than 1 hour remaining
        return datetime.utcnow() < (self.token_expiry - timedelta(hours=1))

    def _ensure_authenticated(self):
        """Ensure we have a valid auth token, refresh if needed"""
        if not self._is_token_valid():
            logger.info("Token expired or missing, re-authenticating...")
            if not self.authenticate():
                raise Exception("Failed to authenticate with Kalshi API")

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
        """
        self._ensure_authenticated()
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=json_data, timeout=10)
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

    def get_markets(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get list of markets with optional filters

        Args:
            status: Filter by status (e.g., 'open', 'closed', 'settled')
            category: Filter by category
            limit: Max number of markets to return

        Returns:
            List of market dictionaries
        """
        params = {'limit': limit}
        if status:
            params['status'] = status
        if category:
            params['series_ticker'] = category

        try:
            response = self._request('GET', '/markets', params=params)
            markets = response.get('markets', [])
            logger.debug(f"Retrieved {len(markets)} markets")
            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            return []

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
