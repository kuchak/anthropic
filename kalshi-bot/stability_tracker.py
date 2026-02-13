"""
Stability Tracker - Tracks when markets first hit 90¢ and enforces wait times.

This is the CRITICAL missing piece that prevents premature betting on unstable prices.

Key features:
1. Tracks first-touch time when market hits 90¢
2. Enforces ticker-specific wait times (1-5 minutes)
3. Resets timer if price drops below 90¢
4. Only allows betting after wait period + price still >= 90¢
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from logger_setup import get_logger

logger = get_logger("stability_tracker")


class StabilityTracker:
    """
    Tracks price stability for markets to prevent premature betting.

    The backtest showed that 58% of markets drop back below 90¢ before stabilizing.
    This tracker ensures we only bet after the price has HELD above 90¢ for the
    required wait time (ticker-specific: 1-5 minutes).
    """

    def __init__(self, config: Dict):
        """
        Initialize stability tracker.

        Args:
            config: Bot configuration with series_ticker_wait_times
        """
        self.config = config

        # Load ticker-specific wait times (in minutes)
        self.wait_times = config.get('series_ticker_wait_times', {})

        # Default wait time if ticker not in config
        self.default_wait_minutes = 3

        # State tracking: {ticker: first_touch_time}
        # When did this market first hit 90¢ in this cycle?
        self.first_touch_times: Dict[str, datetime] = {}

        # State tracking: {ticker: last_seen_price}
        # What was the last price we saw for this market?
        self.last_prices: Dict[str, float] = {}

        logger.info(f"StabilityTracker initialized with {len(self.wait_times)} ticker-specific wait times")

    def check_market(self, ticker: str, current_price: float, price_threshold: float = 0.90) -> bool:
        """
        Check if a market is ready to bet on (stable for required wait time).

        Args:
            ticker: Market ticker
            current_price: Current market price (0.0-1.0)
            price_threshold: Minimum price to consider (default 0.90 for 90¢)

        Returns:
            True if ready to bet (waited long enough + price still >= threshold)
            False if not ready yet (need to wait longer OR price dropped)
        """
        now = datetime.utcnow()

        # Get required wait time for this ticker
        wait_minutes = self.wait_times.get(ticker, self.default_wait_minutes)

        # Get series ticker from full ticker (e.g., "KXNBAGAME-24-01-15-NBA-LAL-BOS" -> "KXNBAGAME")
        series_ticker = self._extract_series_ticker(ticker)
        wait_minutes = self.wait_times.get(series_ticker, self.default_wait_minutes)

        # Check if price is still above threshold
        if current_price < price_threshold:
            # Price dropped below threshold - RESET timer
            if ticker in self.first_touch_times:
                logger.debug(f"⚠️  {ticker}: Price dropped to ${current_price:.2f} - RESETTING timer")
                del self.first_touch_times[ticker]

            self.last_prices[ticker] = current_price
            return False

        # Price is >= threshold
        # Check if we've seen it cross threshold before
        if ticker not in self.first_touch_times:
            # First time seeing this market at/above threshold - START timer
            self.first_touch_times[ticker] = now
            self.last_prices[ticker] = current_price
            logger.info(f"⏱️  {ticker}: First touch at ${current_price:.2f} - waiting {wait_minutes}m")
            return False

        # We've seen this market before - check if enough time has passed
        first_touch_time = self.first_touch_times[ticker]
        elapsed_minutes = (now - first_touch_time).total_seconds() / 60

        # Update last seen price
        self.last_prices[ticker] = current_price

        if elapsed_minutes >= wait_minutes:
            # Enough time has passed AND price is still >= threshold
            logger.info(f"✅ {ticker}: STABLE for {elapsed_minutes:.1f}m (required: {wait_minutes}m) - READY TO BET")
            return True
        else:
            # Not enough time yet - keep waiting
            remaining = wait_minutes - elapsed_minutes
            logger.debug(f"⏳ {ticker}: Held for {elapsed_minutes:.1f}m, need {remaining:.1f}m more")
            return False

    def reset_market(self, ticker: str) -> None:
        """
        Reset tracking for a market (e.g., after placing bet).

        Args:
            ticker: Market ticker to reset
        """
        if ticker in self.first_touch_times:
            del self.first_touch_times[ticker]
        if ticker in self.last_prices:
            del self.last_prices[ticker]

        logger.debug(f"🔄 {ticker}: Reset stability tracking")

    def get_wait_status(self, ticker: str) -> Optional[Dict]:
        """
        Get current wait status for a market.

        Args:
            ticker: Market ticker

        Returns:
            Dict with wait status info, or None if not tracked
        """
        series_ticker = self._extract_series_ticker(ticker)

        if ticker not in self.first_touch_times:
            return None

        now = datetime.utcnow()
        first_touch_time = self.first_touch_times[ticker]
        elapsed_minutes = (now - first_touch_time).total_seconds() / 60
        wait_minutes = self.wait_times.get(series_ticker, self.default_wait_minutes)
        remaining_minutes = max(0, wait_minutes - elapsed_minutes)

        return {
            'ticker': ticker,
            'series_ticker': series_ticker,
            'first_touch_time': first_touch_time,
            'elapsed_minutes': elapsed_minutes,
            'required_wait_minutes': wait_minutes,
            'remaining_minutes': remaining_minutes,
            'ready': elapsed_minutes >= wait_minutes,
            'last_price': self.last_prices.get(ticker, 0.0)
        }

    def cleanup_old_tracking(self, max_age_hours: int = 6) -> int:
        """
        Clean up tracking for markets that haven't been seen in a while.

        Args:
            max_age_hours: Remove tracking for markets older than this

        Returns:
            Number of markets cleaned up
        """
        now = datetime.utcnow()
        cutoff_time = now - timedelta(hours=max_age_hours)

        old_tickers = [
            ticker for ticker, first_touch in self.first_touch_times.items()
            if first_touch < cutoff_time
        ]

        for ticker in old_tickers:
            self.reset_market(ticker)

        if old_tickers:
            logger.info(f"🧹 Cleaned up {len(old_tickers)} old market tracking records")

        return len(old_tickers)

    def get_summary(self) -> Dict:
        """
        Get summary of current tracking state.

        Returns:
            Dict with summary statistics
        """
        now = datetime.utcnow()

        tracked_markets = len(self.first_touch_times)
        ready_markets = sum(
            1 for ticker in self.first_touch_times
            if (now - self.first_touch_times[ticker]).total_seconds() / 60 >=
               self.wait_times.get(self._extract_series_ticker(ticker), self.default_wait_minutes)
        )

        return {
            'tracked_markets': tracked_markets,
            'ready_markets': ready_markets,
            'waiting_markets': tracked_markets - ready_markets
        }

    def _extract_series_ticker(self, full_ticker: str) -> str:
        """
        Extract series ticker from full market ticker.

        Examples:
            "KXNBAGAME-24-01-15-NBA-LAL-BOS" -> "KXNBAGAME"
            "KXBTC15M-24-01-15-15:00" -> "KXBTC15M"

        Args:
            full_ticker: Full market ticker

        Returns:
            Series ticker (first part before hyphen)
        """
        # Series ticker is always the part before the first hyphen
        if '-' in full_ticker:
            return full_ticker.split('-')[0]
        return full_ticker
