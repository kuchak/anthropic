"""
Dynamic series discovery module.

Fetches events from Kalshi API and extracts all unique series_ticker values
grouped by category. This allows the bot to automatically discover new series
without hardcoded whitelists.
"""

import logging
import requests
import time
from typing import Dict, List, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SeriesDiscovery:
    """Discovers and caches series tickers from Kalshi API."""

    def __init__(self, api_base_url: str = "https://api.elections.kalshi.com"):
        self.api_base_url = api_base_url
        self.series_by_category: Dict[str, Set[str]] = {}
        self.last_discovery_time: datetime = None

        # Categories considered "sports" for live event tracking
        self.sports_categories = {
            'Sports', 'Esports', 'sports', 'esports',
            'Basketball', 'Football', 'Baseball', 'Hockey',
            'Soccer', 'Tennis', 'Golf', 'MMA', 'Boxing'
        }

    def discover_series(self, max_pages: int = 10) -> Dict[str, Set[str]]:
        """
        Fetch events from API and extract unique series_ticker values by category.

        Args:
            max_pages: Maximum number of pages to fetch (200 events per page)

        Returns:
            Dictionary mapping category names to sets of series_ticker values
        """
        logger.info(f"Starting series discovery (max {max_pages} pages)...")

        url = f"{self.api_base_url}/trade-api/v2/events"
        series_by_category: Dict[str, Set[str]] = {}
        cursor = None
        page = 0

        while page < max_pages:
            page += 1

            params = {
                'limit': 200
            }

            if cursor:
                params['cursor'] = cursor

            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                events = data.get('events', [])
                cursor = data.get('cursor')

                logger.debug(f"  Page {page}: {len(events)} events")

                # Extract series_ticker from each event
                for event in events:
                    series_ticker = event.get('series_ticker')
                    category = event.get('category', 'Unknown')

                    if series_ticker:
                        if category not in series_by_category:
                            series_by_category[category] = set()
                        series_by_category[category].add(series_ticker)

                # Break if no more pages
                if not cursor or len(events) == 0:
                    break

                # Small delay to avoid rate limiting (100ms between pages)
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error fetching events page {page}: {e}")
                # On rate limit or error, wait longer before breaking
                if "429" in str(e):
                    logger.warning(f"Rate limited on page {page}, stopping discovery")
                    time.sleep(1)
                break

        # Update cached data
        self.series_by_category = series_by_category
        self.last_discovery_time = datetime.now(timezone.utc)

        # Log summary
        total_series = sum(len(series) for series in series_by_category.values())
        logger.info(f"Discovery complete: {total_series} unique series across {len(series_by_category)} categories")

        for category in sorted(series_by_category.keys()):
            count = len(series_by_category[category])
            logger.debug(f"  {category}: {count} series")

        return series_by_category

    def get_sports_series(self) -> List[str]:
        """
        Get all series tickers from sports-related categories.

        Returns:
            List of series_ticker values for sports categories
        """
        sports_series = set()

        for category, series_set in self.series_by_category.items():
            if category in self.sports_categories:
                sports_series.update(series_set)

        return sorted(list(sports_series))

    def get_series_by_category(self, category: str) -> List[str]:
        """
        Get all series tickers for a specific category.

        Args:
            category: Category name (e.g., 'Sports', 'Politics', 'Crypto')

        Returns:
            List of series_ticker values for the category
        """
        return sorted(list(self.series_by_category.get(category, set())))

    def get_all_categories(self) -> List[str]:
        """Get list of all discovered categories."""
        return sorted(list(self.series_by_category.keys()))

    def get_stats(self) -> Dict:
        """Get discovery statistics."""
        total_series = sum(len(series) for series in self.series_by_category.values())
        sports_series = self.get_sports_series()

        return {
            'total_categories': len(self.series_by_category),
            'total_series': total_series,
            'sports_series_count': len(sports_series),
            'last_discovery': self.last_discovery_time.isoformat() if self.last_discovery_time else None,
            'categories': {cat: len(series) for cat, series in self.series_by_category.items()}
        }
