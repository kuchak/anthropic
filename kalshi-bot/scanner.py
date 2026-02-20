"""
Market Scanner
Discovers markets, filters by criteria, and maintains active watchlist

Two-tier scanning system:
- FULL SCAN (every 10 min): Discover all series, scan each, update hot list
- HOT SCAN (every 30 sec): Only scan series with active markets (hot list)
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
from logger_setup import get_logger
from models import Market
from kalshi_client import KalshiClient
from series_discovery import SeriesDiscovery

logger = get_logger("scanner")


class Scanner:
    """
    Scans Kalshi markets and maintains a filtered watchlist

    Two-tier scanning:
    - Full scan: All series discovery + hot list refresh (every 10 min)
    - Hot scan: Only active series for fast opportunity detection (every 30 sec)
    """

    def __init__(self, client: KalshiClient, config: Dict[str, Any]):
        self.client = client
        self.config = config

        # Watchlist of markets that meet our criteria
        self.watchlist: List[Market] = []

        # Legacy tracking (kept for backward compat)
        self.last_slow_scan: Optional[datetime] = None
        self.last_fast_scan: Optional[datetime] = None

        # Two-tier scanning state
        self.hot_series: Set[str] = set()       # Series with active markets (refreshed on full scan)
        self.all_series: List[str] = []         # All discovered series
        self.last_full_scan: Optional[datetime] = None
        self.last_hot_scan: Optional[datetime] = None
        self._series_with_live_markets: Set[str] = set()  # Populated during slow_scan

        # Series discovery
        api_base = config.get('kalshi_api_base', 'https://api.elections.kalshi.com/trade-api/v2')
        base_url = api_base.replace('/trade-api/v2', '')
        self.series_discovery = SeriesDiscovery(api_base_url=base_url)

        logger.info("Scanner initialized (two-tier scanning)")

        hot_interval = config.get('hot_scan_interval_seconds', 30)
        full_interval = config.get('full_scan_interval_seconds', 600)
        logger.info(f"  Hot scan: every {hot_interval}s | Full scan: every {full_interval}s")
        logger.info(f"  FILTERS: (1) mve_filter=exclude (no parlays), (2) price 85-97¢, (3) status=open/active")
        logger.info(f"  Price range: ${config['min_contract_price']:.2f} - ${config['max_contract_price']:.2f}")
        logger.info(f"  Filtering out: MULTIGAME parlays (server-side via mve_filter)")
        logger.info(f"  Volume filter: REMOVED (API doesn't report correctly)")

    def slow_scan(self, existing_position_tickers: Optional[List[str]] = None,
                  series_list: Optional[List[str]] = None) -> int:
        """
        Full market discovery scan

        Queries discovered series for active markets expiring within 3 hours.
        Filters by price range and applies stability tracking criteria.

        Args:
            existing_position_tickers: List of tickers we already have positions in
            series_list: List of series tickers to query (from dynamic discovery)

        Returns:
            Number of markets added to watchlist
        """
        if existing_position_tickers is None:
            existing_position_tickers = []

        if series_list is None:
            series_list = []

        existing_set = set(existing_position_tickers)

        logger.info("🔍 Starting slow scan (dynamic series discovery)...")
        if existing_set:
            logger.info(f"  Filtering out {len(existing_set)} existing positions")

        logger.info(f"  Querying {len(series_list)} discovered series...")

        all_markets = []
        seen_tickers = set()

        # Query each discovered series
        for series in series_list:
            logger.debug(f"  Querying {series}...")
            try:
                series_markets = self.client.get_markets(
                    category=series,
                    mve_filter='exclude',
                    limit=1000,
                    max_total=3000  # Reasonable limit per series
                )
                # Deduplicate
                for m in series_markets:
                    ticker = m.get('ticker', '')
                    if ticker not in seen_tickers:
                        all_markets.append(m)
                        seen_tickers.add(ticker)
            except Exception as e:
                logger.debug(f"  Error querying {series}: {e}")
                continue

        logger.info(f"  Retrieved {len(all_markets)} markets total")

        # Filter for markets expiring within 3 hours (live events)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        cutoff_time = now + timedelta(hours=3)

        markets_expiring_soon = []
        for m in all_markets:
            exp_time = m.get('expected_expiration_time')
            status = m.get('status', '')

            # Only include active markets (not finalized/closed/settled)
            if status not in ['active', 'initialized', 'open']:
                continue

            if exp_time:
                try:
                    from dateutil.parser import parse as parse_datetime
                    exp_dt = parse_datetime(exp_time)

                    # Only include markets expiring within 3 hours
                    if now < exp_dt <= cutoff_time:
                        markets_expiring_soon.append(m)
                except:
                    pass

        logger.info(f"  {len(markets_expiring_soon)} markets expiring within 3 hours")

        # Track which series have live markets (for hot list refresh)
        self._series_with_live_markets = set()
        for m in markets_expiring_soon:
            ticker = m.get('ticker', '')
            series_ticker = ticker.split('-')[0] if '-' in ticker else ticker
            self._series_with_live_markets.add(series_ticker)
        logger.info(f"  {len(self._series_with_live_markets)} series have live markets")

        all_markets = markets_expiring_soon

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

            # NOTE: MULTIGAME parlays now filtered server-side via mve_filter='exclude'
            # No need for client-side filtering anymore

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
        # REMOVED is_live filter - it excludes NCAA basketball and other active markets
        # Server-side filter: (1) mve_filter=exclude (no MULTIGAME parlays)
        # Client-side filters: (2) price 85-97¢, (3) settlement time window, (4) status=open/active

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
        """Check if it's time for a slow scan (legacy)"""
        if not self.last_slow_scan:
            return True

        elapsed = (datetime.utcnow() - self.last_slow_scan).total_seconds() / 60
        return elapsed >= self.config.get('slow_scan_interval_minutes', 0.5)

    def should_run_fast_scan(self) -> bool:
        """Check if it's time for a fast scan (legacy)"""
        if not self.last_fast_scan:
            return True

        elapsed = (datetime.utcnow() - self.last_fast_scan).total_seconds() / 60
        return elapsed >= self.config.get('fast_scan_interval_minutes', 0.5)

    # ── Two-Tier Scanning ────────────────────────────────────────────

    def full_scan(self, existing_position_tickers: Optional[List[str]] = None) -> int:
        """
        Full scan: discover ALL series, scan each, rebuild hot list.
        Runs every 10 minutes.

        Steps:
        1. Discover all series from Kalshi events API
        2. Query each series for active markets expiring within 3 hours
        3. Update hot list = series that had at least one live market

        Returns:
            Number of markets on watchlist
        """
        logger.info("=" * 60)
        logger.info("FULL SCAN: Discovering all series...")
        logger.info("=" * 60)

        # Step 1: Discover all series from API
        max_pages = self.config.get('series_discovery_pages', 100)
        series_by_category = self.series_discovery.discover_series(max_pages=max_pages)

        # Flatten to list of all series tickers
        all_series_set: Set[str] = set()
        for cat_series in series_by_category.values():
            all_series_set.update(cat_series)
        self.all_series = sorted(all_series_set)

        logger.info(f"Discovered {len(self.all_series)} total series across {len(series_by_category)} categories")

        # Step 2: Scan all series (reuses slow_scan core logic)
        count = self.slow_scan(
            existing_position_tickers=existing_position_tickers,
            series_list=self.all_series
        )

        # Step 3: Update hot list from scan results
        # _series_with_live_markets is populated during slow_scan (before price filtering)
        # so it includes series with active games regardless of current price
        old_hot = self.hot_series.copy()
        self.hot_series = self._series_with_live_markets.copy()
        self.last_full_scan = datetime.utcnow()
        self.last_hot_scan = self.last_full_scan  # Full scan covers hot scan too

        # Log hot list changes
        new_hot = self.hot_series - old_hot
        removed_hot = old_hot - self.hot_series

        logger.info("")
        logger.info(f"HOT LIST: {len(self.hot_series)} series with active markets (of {len(self.all_series)} total)")
        for s in sorted(self.hot_series):
            tag = " [NEW]" if s in new_hot else ""
            logger.info(f"  {s}{tag}")
        if removed_hot:
            logger.info(f"  Cooled off: {sorted(removed_hot)}")

        print(f"\n🔥 HOT LIST: {len(self.hot_series)} series (of {len(self.all_series)} total)")
        for s in sorted(self.hot_series):
            print(f"  → {s}")
        print()

        return count

    def hot_scan(self, existing_position_tickers: Optional[List[str]] = None) -> int:
        """
        Hot scan: only query series on the hot list.
        Runs every 30 seconds for fast market discovery.

        If hot list is empty, falls back to full scan.

        Returns:
            Number of markets on watchlist
        """
        if not self.hot_series:
            logger.info("No hot series — triggering full scan")
            return self.full_scan(existing_position_tickers)

        logger.info(f"HOT SCAN: {len(self.hot_series)} series → {sorted(self.hot_series)}")

        count = self.slow_scan(
            existing_position_tickers=existing_position_tickers,
            series_list=sorted(self.hot_series)
        )

        self.last_hot_scan = datetime.utcnow()

        return count

    def should_run_full_scan(self) -> bool:
        """Check if it's time for a full scan (every 10 minutes)."""
        if not self.last_full_scan:
            return True
        elapsed = (datetime.utcnow() - self.last_full_scan).total_seconds()
        interval = self.config.get('full_scan_interval_seconds', 600)
        return elapsed >= interval

    def should_run_hot_scan(self) -> bool:
        """Check if it's time for a hot scan (every 30 seconds)."""
        if not self.last_hot_scan:
            return True  # Will trigger full scan via hot_scan fallback
        elapsed = (datetime.utcnow() - self.last_hot_scan).total_seconds()
        interval = self.config.get('hot_scan_interval_seconds', 30)
        return elapsed >= interval
