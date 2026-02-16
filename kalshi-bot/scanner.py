"""
Market Scanner
Discovers markets, filters by criteria, and maintains active watchlist
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
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

        logger.info(f"  FILTERS: (1) is_live=true, (2) not MULTIGAME, (3) price 85-97¢")
        logger.info(f"  Price range: ${config['min_contract_price']:.2f} - ${config['max_contract_price']:.2f}")
        logger.info(f"  Filtering out: Synthetic MULTIGAME parlays")
        logger.info(f"  Volume filter: REMOVED (API doesn't report correctly)")

    def slow_scan(self, existing_position_tickers: Optional[List[str]] = None) -> int:
        """
        Full market discovery scan

        Evaluates ALL active markets (no category filtering):
        - Settlement time within window
        - Price in target range
        - NOT in existing positions (prevents duplicate positions)

        Decision making is purely based on scoring: model accuracy by price range,
        expected profit after fees, and time to settlement.

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

        # Get live markets - filter out synthetic parlays client-side
        # is_live=true returns ~5000 markets including live sports
        # We filter out MULTIGAME parlays and rely on price filter
        logger.info(f"  Querying live markets (is_live=true)...")
        all_markets = self.client.get_markets(
            is_live='true',
            limit=1000,
            max_total=5000
        )
        logger.info(f"  Retrieved {len(all_markets)} live markets")

        # Debug counters
        filter_stats = {
            'total': len(all_markets),
            'existing_position': 0,
            'parse_failed': 0,
            'not_whitelisted': 0,
            'wrong_price': 0,
            'wrong_settlement': 0,
            'wrong_status': 0,
            'not_live': 0,
            'passed': 0
        }

        # Filter markets
        new_watchlist = []
        seen_events = {}  # Track events to prevent dual-side betting

        for market_data in all_markets:
            ticker = market_data.get('ticker', '')

            # CRITICAL: Skip markets where we already have positions
            if ticker in existing_set:
                logger.debug(f"  Skipping {ticker} - already have position")
                filter_stats['existing_position'] += 1
                continue

            # Skip synthetic parlay markets (MULTIGAME) - they have no real trading
            if 'MULTIGAME' in ticker:
                logger.debug(f"  Skipping {ticker} - synthetic parlay")
                filter_stats['parse_failed'] += 1  # Count as parse failed
                continue

            # Extract event identifier (everything except the last outcome part)
            # E.g., "KXATPMATCH-26FEB13SIMBAR-SIM" -> "KXATPMATCH-26FEB13SIMBAR"
            # This prevents betting YES and NO on the same event
            event_id = '-'.join(ticker.split('-')[:-1]) if ticker.count('-') >= 2 else ticker

            # Skip if we've already added a market for this event
            if event_id in seen_events:
                logger.debug(f"  Skipping {ticker} - already have {seen_events[event_id]} for this event")
                filter_stats['existing_position'] += 1
                continue

            # NO CATEGORY FILTERING - evaluate ALL markets
            # Decision based purely on: price range accuracy, expected profit, time to settlement

            # Parse market
            try:
                market = self._parse_market_quick(market_data)
                if not market:
                    filter_stats['parse_failed'] += 1
                    continue

                # Check criteria and track reason if fails
                if not self._meets_criteria_with_debug(market, filter_stats):
                    continue

                new_watchlist.append(market)
                filter_stats['passed'] += 1
                # Mark this event as seen to prevent dual-side betting
                seen_events[event_id] = ticker

            except Exception as e:
                logger.debug(f"  Failed to parse market {market_data.get('ticker')}: {e}")
                filter_stats['parse_failed'] += 1
                continue

        # Update watchlist
        old_count = len(self.watchlist)
        self.watchlist = new_watchlist
        self.last_slow_scan = datetime.utcnow()

        logger.info(f"✅ Slow scan complete")
        logger.info(f"  Watchlist: {len(self.watchlist)} markets (was {old_count})")
        logger.info(f"  Filter breakdown:")
        logger.info(f"    Total markets: {filter_stats['total']}")
        logger.info(f"    Existing positions: {filter_stats['existing_position']}")
        logger.info(f"    Parse failed: {filter_stats['parse_failed']}")
        logger.info(f"    Not whitelisted: {filter_stats['not_whitelisted']}")
        logger.info(f"    Wrong price: {filter_stats['wrong_price']}")
        logger.info(f"    Wrong settlement time: {filter_stats['wrong_settlement']}")
        logger.info(f"    Wrong status: {filter_stats['wrong_status']}")
        logger.info(f"    Not live event (future or stale): {filter_stats['not_live']}")
        logger.info(f"    ✅ PASSED: {filter_stats['passed']}")

        # Also print to stdout for debugging
        print(f"\n🔍 SCANNER FILTER BREAKDOWN:")
        print(f"  Total markets from API: {filter_stats['total']}")
        print(f"  Already have positions: {filter_stats['existing_position']}")
        print(f"  Parse failed: {filter_stats['parse_failed']}")
        print(f"  Not in whitelist: {filter_stats['not_whitelisted']}")
        print(f"  Wrong price (not 85-97¢): {filter_stats['wrong_price']}")
        print(f"  Wrong settlement time: {filter_stats['wrong_settlement']}")
        print(f"  Wrong status (not open): {filter_stats['wrong_status']}")
        print(f"  Not a live event (future market or stale activity): {filter_stats['not_live']}")
        print(f"  ✅ PASSED ALL FILTERS: {filter_stats['passed']}\n")

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

            # Extract series ticker from ticker field
            # Format: KXEPLGAME-26FEB28LEEMCI-TIE -> KXEPLGAME
            ticker = market_data['ticker']
            series_ticker = ticker.split('-')[0] if '-' in ticker else ticker

            # Get volume (use volume_24h_fp if available, otherwise volume_24h)
            volume_24h = float(market_data.get('volume_24h_fp', 0) or market_data.get('volume_24h', 0) or 0)

            # Store raw market data for additional checks
            market = Market(
                ticker=ticker,
                title=market_data['title'],
                category=series_ticker,
                settlement_time=parse_datetime(market_data['close_time']),
                status=market_data['status'],
                best_yes_price=yes_price,
                best_no_price=no_price,
                best_yes_size=0,  # Size not critical for scanning
                best_no_size=0,
                volume_24h=volume_24h
            )

            # Store additional metadata for live event detection
            market._raw_data = {
                'expected_expiration_time': market_data.get('expected_expiration_time'),
                'updated_time': market_data.get('updated_time')
            }

            return market

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
        # NO WHITELIST - scan all markets

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

        # Check market is open/active (API returns 'active' status for open markets)
        if market.status not in ['open', 'active']:
            return False

        return True

    def _meets_criteria_with_debug(self, market: Market, filter_stats: Dict[str, int]) -> bool:
        """
        Check if market meets criteria and track reason for failure

        Args:
            market: Market to check
            filter_stats: Dict to update with failure reason

        Returns:
            True if market meets all criteria
        """
        # NO WHITELIST - scan all markets

        # Check settlement time window
        time_to_settlement_minutes = market.time_to_settlement_minutes

        if time_to_settlement_minutes < self.config['min_time_to_settlement_minutes']:
            filter_stats['wrong_settlement'] += 1
            return False  # Too close to settlement

        if time_to_settlement_minutes > self.config['max_time_to_settlement_hours'] * 60:
            filter_stats['wrong_settlement'] += 1
            return False  # Too far out

        # Check price range (either YES or NO must be in range)
        min_price = self.config['min_contract_price']
        max_price = self.config['max_contract_price']

        yes_in_range = min_price <= market.best_yes_price <= max_price
        no_in_range = min_price <= market.best_no_price <= max_price

        if not (yes_in_range or no_in_range):
            filter_stats['wrong_price'] += 1
            return False  # Neither side in target range

        # VERBOSE: Log markets that pass price filter
        side = "YES" if yes_in_range else "NO"
        price = market.best_yes_price if yes_in_range else market.best_no_price
        print(f"✅ PRICE MATCH: {market.ticker} | {side}={price:.2f}¢ | {market.title[:60]}")
        logger.info(f"✅ Price filter passed: {market.ticker} | {side}={price:.2f}¢")

        # Check market is open/active (API returns 'active' status for open markets)
        if market.status not in ['open', 'active']:
            filter_stats['wrong_status'] += 1
            return False

        # REMOVED volume check - API doesn't report volume correctly (always 0)
        # REMOVED time check - is_live=true already filters for live events
        # Only filters: (1) is_live=true, (2) not MULTIGAME, (3) price 85-97¢

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
