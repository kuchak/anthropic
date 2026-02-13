"""
Fetch market open times from Kalshi API in bulk.

Strategy: Fetch markets by series_ticker (one API call per series)
instead of fetching individual markets (9,000+ API calls).

GET /markets?series_ticker=KXNBAGAME&limit=1000&cursor=...
"""

import pandas as pd
import requests
import time
import json
from pathlib import Path

# API setup
API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get_markets_by_series(series_ticker, session):
    """Fetch all markets for a given series ticker with pagination."""
    markets = []
    cursor = None
    page = 1

    while True:
        params = {
            'series_ticker': series_ticker,
            'limit': 1000,
            'status': 'settled'  # Only get settled markets
        }
        if cursor:
            params['cursor'] = cursor

        # Retry with exponential backoff
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = session.get(f"{API_BASE}/markets", params=params)
                response.raise_for_status()
                data = response.json()

                batch = data.get('markets', [])
                markets.extend(batch)

                print(f"  Page {page}: fetched {len(batch)} markets (total: {len(markets)})")

                cursor = data.get('cursor')
                if not cursor or not batch:
                    return markets

                page += 1
                time.sleep(0.5)  # Rate limiting between pages
                break  # Success, exit retry loop

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                    print(f"  Rate limit hit on page {page}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    if attempt == max_retries - 1:
                        print(f"  ⚠️  Failed after {max_retries} attempts, skipping remaining pages")
                        return markets
                else:
                    print(f"  Error fetching page {page}: {e}")
                    return markets
            except Exception as e:
                print(f"  Error fetching page {page}: {e}")
                return markets

    return markets

def extract_market_times(market):
    """Extract ticker, open_time, close_time from market object."""
    return {
        'ticker': market.get('ticker'),
        'series_ticker': market.get('series_ticker'),
        'open_time': market.get('open_time'),
        'close_time': market.get('close_time'),
        'settlement_date': market.get('settlement_date'),
        'status': market.get('status')
    }

def main():
    print("Loading CSV to get unique series tickers...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Get unique series tickers
    series_tickers = df['Series Ticker'].unique()
    series_tickers = [st for st in series_tickers if pd.notna(st)]
    series_tickers = sorted(series_tickers)  # Sort for consistent ordering

    print(f"Found {len(series_tickers)} unique series tickers")
    print()

    # Check for existing checkpoint to resume
    all_market_times = []
    completed_series = set()

    if Path('market_times_checkpoint.csv').exists():
        print("Found existing checkpoint, loading...")
        checkpoint_df = pd.read_csv('market_times_checkpoint.csv')
        all_market_times = checkpoint_df.to_dict('records')
        completed_series = set(checkpoint_df['series_ticker'].unique())
        print(f"Resuming from checkpoint: {len(all_market_times)} markets, {len(completed_series)} series completed")
        print()

    # Create session
    session = requests.Session()

    # Fetch markets for each series
    remaining_series = [st for st in series_tickers if st not in completed_series]

    print(f"Fetching {len(remaining_series)} remaining series...")
    print()

    for idx, series_ticker in enumerate(remaining_series, 1):
        print(f"[{idx}/{len(remaining_series)}] Fetching {series_ticker}...")

        markets = get_markets_by_series(series_ticker, session)

        for market in markets:
            market_data = extract_market_times(market)
            all_market_times.append(market_data)

        print(f"  ✓ Total markets for {series_ticker}: {len(markets)}")
        print()

        # Rate limit between series
        time.sleep(1)

        # Save checkpoint every 5 series
        if idx % 5 == 0:
            checkpoint_df = pd.DataFrame(all_market_times)
            checkpoint_df.to_csv('market_times_checkpoint.csv', index=False)
            print(f"💾 Checkpoint saved: {len(all_market_times)} markets so far")
            print()

    # Save final results
    print("=" * 80)
    print("Saving final results...")

    market_times_df = pd.DataFrame(all_market_times)
    market_times_df.to_csv('market_open_close_times.csv', index=False)

    print(f"✅ Saved {len(market_times_df)} market times to market_open_close_times.csv")
    print()

    # Summary
    print("Summary:")
    print(f"  Unique tickers: {market_times_df['ticker'].nunique()}")
    print(f"  Unique series: {market_times_df['series_ticker'].nunique()}")
    print(f"  Markets with open_time: {market_times_df['open_time'].notna().sum()}")
    print(f"  Markets with close_time: {market_times_df['close_time'].notna().sum()}")
    print()

    # Show sample
    print("Sample:")
    print(market_times_df.head(10))

if __name__ == "__main__":
    main()
