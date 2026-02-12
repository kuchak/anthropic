"""
Market Scanner
Discovers markets, filters by criteria, and maintains active watchlist
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from logger_setup import get_logger
from models import Market
from kalshi_client import KalshiClient

logger = get_logger("scanner")


class Scanner:
    """
    Scans Kalshi markets and maintains a filtered watchlist

    Two scanning modes:
    - Slow scan: Full market discovery (every 15 min)
    - Fast scan: Watchlist price updates (every 3 min)
    """

    def __init__(self, client: KalshiClient, config: Dict[str, Any]):
        self.client = client
        self.config = config

        # Watchlist of markets that meet our criteria
        self.watchlist: List[Market] = []

        # Tracking
        self.last_slow_scan: Optional[datetime] = None
        self.last_fast_scan: Optional[datetime] = None

        logger.info("Scanner initialized")
        logger.info(f"  Approved categories: {config['approved_categories']}")
        logger.info(f"  Price range: ${config['min_contract_price']:.2f} - ${config['max_contract_price']:.2f}")
        logger.info(f"  Settlement window: {config['min_time_to_settlement_minutes']}m - {config['max_time_to_settlement_hours']}h")

    def slow_scan(self, existing_position_tickers: Optional[List[str]] = None) -> int:
        """
        Full market discovery scan

        Finds all active markets that meet our criteria:
        - In approved categories
        - Settlement time within window
        - Price in target range
        - NOT in existing positions (prevents duplicate positions)

        Args:
            existing_position_tickers: List of tickers we already have positions in

        Returns:
            Number of markets added to watchlist
        """
        if existing_position_tickers is None:
            existing_position_tickers = []

        existing_set = set(existing_position_tickers)

        logger.info("🔍 Starting slow scan (full market discovery)...")
        if existing_set:
            logger.info(f"  Filtering out {len(existing_set)} existing positions")

        # Get all open markets
        all_markets = self.client.get_markets(status='open', limit=1000)
        logger.info(f"  Retrieved {len(all_markets)} total open markets")

        # Filter markets
        new_watchlist = []

        for market_data in all_markets:
            ticker = market_data.get('ticker', '')

            # CRITICAL: Skip markets where we already have positions
            if ticker in existing_set:
                logger.debug(f"  Skipping {ticker} - already have position")
                continue

            # Check category filter
            category = market_data.get('series_ticker', '')

            # Match against approved categories (prefix matching)
            if not any(category.lower().startswith(cat.lower()) for cat in self.config['approved_categories']):
                continue

            # Parse market
            try:
                market = self._parse_market_quick(market_data)
                if market and self._meets_criteria(market):
                    new_watchlist.append(market)
            except Exception as e:
                logger.debug(f"  Failed to parse market {market_data.get('ticker')}: {e}")
                continue

        # Update watchlist
        old_count = len(self.watchlist)
        self.watchlist = new_watchlist
        self.last_slow_scan = datetime.utcnow()

        logger.info(f"✅ Slow scan complete")
        logger.info(f"  Watchlist: {len(self.watchlist)} markets (was {old_count})")

        return len(self.watchlist)

    def fast_scan(self, existing_position_tickers: Optional[List[str]] = None) -> int:
        """
        Fast price update scan

        Updates prices for markets on the watchlist
        Removes markets that no longer meet criteria or where we have positions

        Args:
            existing_position_tickers: List of tickers we already have positions in

        Returns:
            Number of markets still on watchlist
        """
        if not self.watchlist:
            logger.debug("Fast scan skipped - watchlist empty")
            return 0

        if existing_position_tickers is None:
            existing_position_tickers = []

        existing_set = set(existing_position_tickers)

        logger.debug(f"⚡ Fast scan - updating {len(self.watchlist)} markets...")
        if existing_set:
            logger.debug(f"  Filtering out {len(existing_set)} existing positions")

        updated_watchlist = []

        for market in self.watchlist:
            # CRITICAL: Skip if we now have a position in this market
            if market.ticker in existing_set:
                logger.debug(f"  Removing {market.ticker} - now have position")
                continue

            try:
                # Get fresh market data
                market_data = self.client.get_market(market.ticker)
                if not market_data:
                    logger.debug(f"  Market {market.ticker} no longer available")
                    continue

                # Re-parse with updated data
                updated_market = self._parse_market_quick(market_data)

                # Check if still meets criteria
                if updated_market and self._meets_criteria(updated_market):
                    updated_watchlist.append(updated_market)
                else:
                    logger.debug(f"  Market {market.ticker} no longer meets criteria")

            except Exception as e:
                logger.debug(f"  Error updating {market.ticker}: {e}")
                continue

        # Update watchlist
        removed = len(self.watchlist) - len(updated_watchlist)
        self.watchlist = updated_watchlist
        self.last_fast_scan = datetime.utcnow()

        if removed > 0:
            logger.info(f"  Removed {removed} markets from watchlist")

        logger.debug(f"✅ Fast scan complete - {len(self.watchlist)} markets active")

        return len(self.watchlist)

    def _parse_market_quick(self, market_data: Dict[str, Any]) -> Optional[Market]:
        """
        Quick market parsing without orderbook fetch
        Uses last price or mid-price approximation

        Args:
            market_data: Raw market data from API

        Returns:
            Market object or None if parsing fails
        """
        try:
            from dateutil.parser import parse as parse_datetime

            # Use last_price or yes_ask/yes_bid for price estimation
            # For actual trading, we'll fetch full orderbook
            # For scanning, last price is sufficient

            yes_price = market_data.get('yes_ask', 0) / 100.0 if market_data.get('yes_ask') else 0.0
            no_price = market_data.get('no_ask', 0) / 100.0 if market_data.get('no_ask') else 0.0

            # Fallback to last price if available
            if yes_price == 0.0:
                yes_price = market_data.get('last_price', 0) / 100.0 if market_data.get('last_price') else 0.0
            if no_price == 0.0:
                no_price = 1.0 - yes_price if yes_price > 0 else 0.0

            return Market(
                ticker=market_data['ticker'],
                title=market_data['title'],
                category=market_data.get('series_ticker', 'unknown'),
                settlement_time=parse_datetime(market_data['close_time']),
                status=market_data['status'],
                best_yes_price=yes_price,
                best_no_price=no_price,
                best_yes_size=0,  # Size not critical for scanning
                best_no_size=0
            )

        except Exception as e:
            logger.debug(f"Quick parse failed for {market_data.get('ticker')}: {e}")
            return None

    def _meets_criteria(self, market: Market) -> bool:
        """
        Check if market meets our trading criteria

        Args:
            market: Market to check

        Returns:
            True if market meets all criteria
        """
        # Check settlement time window
        time_to_settlement_minutes = market.time_to_settlement_minutes

        if time_to_settlement_minutes < self.config['min_time_to_settlement_minutes']:
            return False  # Too close to settlement

        if time_to_settlement_minutes > self.config['max_time_to_settlement_hours'] * 60:
            return False  # Too far out

        # Check price range (either YES or NO must be in range)
        min_price = self.config['min_contract_price']
        max_price = self.config['max_contract_price']

        yes_in_range = min_price <= market.best_yes_price <= max_price
        no_in_range = min_price <= market.best_no_price <= max_price

        if not (yes_in_range or no_in_range):
            return False  # Neither side in target range

        # Check market is open
        if market.status != 'open':
            return False

        return True

    def get_watchlist(self) -> List[Market]:
        """
        Get current watchlist

        Returns:
            List of markets on watchlist
        """
        return self.watchlist.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scanner statistics

        Returns:
            Dictionary of scanner stats
        """
        # Count by category
        by_category: Dict[str, int] = {}
        for market in self.watchlist:
            category = market.category
            by_category[category] = by_category.get(category, 0) + 1

        return {
            'watchlist_size': len(self.watchlist),
            'last_slow_scan': self.last_slow_scan.isoformat() if self.last_slow_scan else None,
            'last_fast_scan': self.last_fast_scan.isoformat() if self.last_fast_scan else None,
            'by_category': by_category
        }

    def should_run_slow_scan(self) -> bool:
        """Check if it's time for a slow scan"""
        if not self.last_slow_scan:
            return True

        elapsed = (datetime.utcnow() - self.last_slow_scan).total_seconds() / 60
        return elapsed >= self.config['slow_scan_interval_minutes']

    def should_run_fast_scan(self) -> bool:
        """Check if it's time for a fast scan"""
        if not self.last_fast_scan:
            return True

        elapsed = (datetime.utcnow() - self.last_fast_scan).total_seconds() / 60
        return elapsed >= self.config['fast_scan_interval_minutes']
