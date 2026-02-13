"""
Estimate market open_time from ticker patterns.

Examples:
- KXNBAGAME-26FEB10 = NBA game on Feb 10, 2026 → 7:00 PM ET
- KXNFLGAME-26FEB09 = NFL game on Feb 9, 2026 → 1:00 PM ET (Sunday)
- KXEPLGAME-26FEB08 = EPL game on Feb 8, 2026 → 10:00 AM ET (3:00 PM UK)
- Tennis/esports: use first_touch_time - typical event duration

This keeps ALL markets in the analysis instead of losing 25.9% to missing API data.
"""

import pandas as pd
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def parse_date_from_ticker(ticker):
    """
    Extract date from ticker patterns like:
    - KXNBAGAME-26FEB10 → 2026-02-10
    - KXNFLGAME-25DEC25 → 2025-12-25
    """
    # Pattern: YYMMMDD (e.g., 26FEB10, 25DEC25)
    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})', ticker)
    if match:
        year_suffix = match.group(1)
        month_str = match.group(2)
        day = match.group(3)

        # Convert to full year (assume 20xx)
        year = f"20{year_suffix}"

        # Parse month
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        month = month_map.get(month_str, '01')

        try:
            date_str = f"{year}-{month}-{day}"
            return pd.to_datetime(date_str)
        except:
            return None

    return None

def estimate_open_time(ticker, series_ticker, first_touch_time):
    """
    Estimate when market opened based on sport/event type.

    Strategy:
    1. Parse event date from ticker
    2. Apply sport-specific timing rules
    3. Fallback to first_touch - typical duration for markets without dates
    """
    event_date = parse_date_from_ticker(ticker)

    # If we can't parse date, use fallback method
    if event_date is None:
        return estimate_from_first_touch(series_ticker, first_touch_time)

    # Convert to ET timezone
    et = ZoneInfo('America/New_York')

    # Sport-specific event start times (all in ET)
    if 'NBA' in series_ticker:
        # NBA games typically 7:00 PM ET
        open_time = event_date.replace(hour=19, minute=0)

    elif 'NFL' in series_ticker:
        # NFL: Sunday 1pm, Monday 8pm, Thursday 8:15pm
        weekday = event_date.weekday()  # 0=Monday, 6=Sunday
        if weekday == 6:  # Sunday
            open_time = event_date.replace(hour=13, minute=0)
        elif weekday == 0:  # Monday
            open_time = event_date.replace(hour=20, minute=0)
        elif weekday == 3:  # Thursday
            open_time = event_date.replace(hour=20, minute=15)
        else:  # Other days (rare)
            open_time = event_date.replace(hour=13, minute=0)

    elif 'NHL' in series_ticker:
        # NHL games typically 7:00 PM ET
        open_time = event_date.replace(hour=19, minute=0)

    elif 'MLB' in series_ticker:
        # MLB games typically 7:00 PM ET
        open_time = event_date.replace(hour=19, minute=0)

    elif 'EPL' in series_ticker or 'BUNDESLIGA' in series_ticker or 'LALIGA' in series_ticker or \
         'SERIEA' in series_ticker or 'LIGUE1' in series_ticker or 'EREDIVISIE' in series_ticker or \
         'SCOTTISHPREM' in series_ticker or 'EFLCHAMPIONSHIP' in series_ticker:
        # European soccer: typically 10:00 AM ET (3:00 PM local)
        weekday = event_date.weekday()
        if weekday == 5:  # Saturday
            open_time = event_date.replace(hour=10, minute=0)
        elif weekday == 6:  # Sunday
            open_time = event_date.replace(hour=11, minute=0)
        else:  # Midweek
            open_time = event_date.replace(hour=15, minute=0)

    elif 'MLS' in series_ticker or 'LIGAMX' in series_ticker:
        # MLS/Liga MX: typically 7:30 PM ET on weekends
        weekday = event_date.weekday()
        if weekday >= 5:  # Weekend
            open_time = event_date.replace(hour=19, minute=30)
        else:  # Midweek
            open_time = event_date.replace(hour=19, minute=30)

    elif 'UCL' in series_ticker or 'UEL' in series_ticker or 'UECL' in series_ticker:
        # Champions/Europa League: typically 3:00 PM ET (9:00 PM CET)
        open_time = event_date.replace(hour=15, minute=0)

    elif 'ATP' in series_ticker or 'WTA' in series_ticker or 'FOMEN' in series_ticker or 'FOWOMEN' in series_ticker:
        # Tennis: typically 12:00 PM ET (varies by tournament)
        open_time = event_date.replace(hour=12, minute=0)

    elif 'CS2' in series_ticker or 'CSGO' in series_ticker or 'DOTA2' in series_ticker or \
         'LOL' in series_ticker or 'COD' in series_ticker or 'VALORANT' in series_ticker:
        # Esports: typically 12:00 PM ET
        open_time = event_date.replace(hour=12, minute=0)

    elif 'F1' in series_ticker:
        # F1 races: typically 9:00 AM ET (2:00 PM CET for European races)
        open_time = event_date.replace(hour=9, minute=0)

    elif 'CRICKET' in series_ticker:
        # Cricket: typically 10:00 AM ET
        open_time = event_date.replace(hour=10, minute=0)

    elif 'HIGH' in series_ticker or 'LOWT' in series_ticker or 'RAIN' in series_ticker:
        # Weather: markets typically resolve at end of day, open at midnight
        open_time = event_date.replace(hour=0, minute=0)

    elif 'CPI' in series_ticker or 'GDP' in series_ticker or 'JOBLESS' in series_ticker:
        # Economic data: typically released 8:30 AM ET
        open_time = event_date.replace(hour=8, minute=30)

    elif 'GAS' in series_ticker or 'AAAGA' in series_ticker:
        # Energy prices: typically 10:30 AM ET (EIA release time)
        open_time = event_date.replace(hour=10, minute=30)

    elif 'BTC' in series_ticker or 'ETH' in series_ticker or 'XRP' in series_ticker or 'SOL' in series_ticker:
        # Crypto: 15-minute markets, use first_touch - 7.5 minutes
        return first_touch_time - timedelta(minutes=7.5)

    elif 'MENTION' in series_ticker:
        # Mentions: typically daily markets, midnight to midnight
        open_time = event_date.replace(hour=0, minute=0)

    elif 'CASED' in series_ticker:
        # COVID cases: daily markets, midnight
        open_time = event_date.replace(hour=0, minute=0)

    elif 'FLIGHT' in series_ticker:
        # Flight delays: typically resolve end of day
        open_time = event_date.replace(hour=6, minute=0)

    elif 'HURCAT' in series_ticker:
        # Hurricane category: typically open when storm forms
        # Use first_touch - 24 hours as estimate
        return first_touch_time - timedelta(hours=24)

    else:
        # Default: use first_touch - 12 hours
        return first_touch_time - timedelta(hours=12)

    # Set timezone to ET
    try:
        open_time = open_time.replace(tzinfo=et)
    except:
        # Already timezone-aware or error
        pass

    return open_time

def estimate_from_first_touch(series_ticker, first_touch_time):
    """
    Fallback: estimate open_time from first_touch_time - typical event duration.
    """
    # Sport-specific typical durations before first touch
    if 'NBA' in series_ticker or 'NFL' in series_ticker or 'NHL' in series_ticker:
        # Games: typically touch 90¢ near end, so ~2 hours before
        return first_touch_time - timedelta(hours=2)

    elif 'MLB' in series_ticker:
        # Baseball: ~2.5 hours
        return first_touch_time - timedelta(hours=2.5)

    elif 'SOCCER' in series_ticker or 'EPL' in series_ticker or any(x in series_ticker for x in
        ['BUNDESLIGA', 'LALIGA', 'LIGUE1', 'SERIEA', 'MLS', 'UCL', 'UEL']):
        # Soccer: ~1.5 hours (90 min + stoppage)
        return first_touch_time - timedelta(hours=1.5)

    elif 'TENNIS' in series_ticker or 'ATP' in series_ticker or 'WTA' in series_ticker:
        # Tennis: ~2 hours average
        return first_touch_time - timedelta(hours=2)

    elif 'ESPORTS' in series_ticker or any(x in series_ticker for x in ['CS2', 'CSGO', 'DOTA2', 'LOL']):
        # Esports: ~1.5 hours
        return first_touch_time - timedelta(hours=1.5)

    elif '15M' in series_ticker:
        # 15-minute crypto markets
        return first_touch_time - timedelta(minutes=7.5)

    elif 'MENTION' in series_ticker or 'CPI' in series_ticker or 'GDP' in series_ticker:
        # Daily markets or economic data
        return first_touch_time - timedelta(hours=12)

    else:
        # Default: 12 hours before first touch
        return first_touch_time - timedelta(hours=12)

def main():
    print("=" * 100)
    print("ESTIMATING OPEN TIMES FROM TICKERS")
    print("=" * 100)
    print()

    # Load data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')
    print(f"Loaded {len(df):,} markets")

    # Parse timestamps
    df['First_Touch_DT'] = pd.to_datetime(df['First Touch Time'], format='ISO8601')
    df['CSV_Close_DT'] = pd.to_datetime(df['Market Close Time'], format='ISO8601')

    # Estimate open times
    print("Estimating open times from tickers...")
    df['Estimated_Open_DT'] = df.apply(
        lambda row: estimate_open_time(row['Ticker'], row['Series Ticker'], row['First_Touch_DT']),
        axis=1
    )

    # Calculate timing metrics
    # Convert to pandas datetime, handling timezones
    df['Estimated_Open_DT'] = pd.to_datetime(df['Estimated_Open_DT'], utc=True)

    df['Market_Duration_Hours'] = (df['CSV_Close_DT'] - df['Estimated_Open_DT']).dt.total_seconds() / 3600
    df['Time_Elapsed_At_First_Touch'] = (df['First_Touch_DT'] - df['Estimated_Open_DT']).dt.total_seconds() / 3600
    df['First_Touch_Pct'] = (df['Time_Elapsed_At_First_Touch'] / df['Market_Duration_Hours']) * 100

    # Show sample
    print("\nSample estimations:")
    print("-" * 100)
    sample = df[['Ticker', 'Series Ticker', 'Estimated_Open_DT', 'First_Touch_DT', 'CSV_Close_DT',
                  'Market_Duration_Hours', 'First_Touch_Pct']].head(10)
    for idx, row in sample.iterrows():
        print(f"\n{row['Ticker']}")
        print(f"  Series: {row['Series Ticker']}")
        print(f"  Open:   {row['Estimated_Open_DT']}")
        print(f"  Touch:  {row['First_Touch_DT']}")
        print(f"  Close:  {row['CSV_Close_DT']}")
        print(f"  Duration: {row['Market_Duration_Hours']:.1f} hours")
        print(f"  Touch at: {row['First_Touch_Pct']:.1f}% of market life")

    print()
    print("=" * 100)

    # Check for anomalies
    negative = (df['First_Touch_Pct'] < 0).sum()
    over_100 = (df['First_Touch_Pct'] > 100).sum()
    valid = ((df['First_Touch_Pct'] >= 0) & (df['First_Touch_Pct'] <= 100)).sum()

    print(f"Data quality with estimated open times:")
    print(f"  Valid (0-100%): {valid:,} ({valid/len(df)*100:.1f}%)")
    print(f"  Negative: {negative:,} ({negative/len(df)*100:.1f}%)")
    print(f"  Over 100%: {over_100:,} ({over_100/len(df)*100:.1f}%)")
    print()

    # Save with estimated open times
    df.to_csv('comprehensive_with_estimated_open_times.csv', index=False)
    print(f"✅ Saved to comprehensive_with_estimated_open_times.csv")
    print()

if __name__ == "__main__":
    main()
