"""
Show ALL series tickers from backtest - not just profitable ones.

User wants to see everything so they can make informed decisions about:
1. Seasonal tickers (NCAA, NFL, NBA, etc.)
2. Year-round tickers (crypto, weather, mentions, etc.)
3. Which tickers to include even if below 91%

Shows complete picture with accuracy, profitability, sample size, and category.
"""

import pandas as pd
import math

def calculate_expected_profit(price, accuracy, fee_rate=0.07):
    """Calculate expected profit per bet"""
    fee = math.ceil(fee_rate * price * (1.0 - price) * 100) / 100
    total_cost = price + fee
    profit_if_win = 1.00 - total_cost
    loss_if_lose = -total_cost
    expected = (accuracy/100 * profit_if_win) + ((1 - accuracy/100) * loss_if_lose)
    return expected

def main():
    print("=" * 120)
    print("ALL SERIES TICKERS FROM BACKTEST (90-92¢ range)")
    print("=" * 120)
    print()

    # Load backtest data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Filter to 90-92¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Total markets in 90-92¢ range: {len(price_df):,}")
    print()

    # Calculate accuracy by series ticker
    ticker_stats = []

    for ticker in df['Series Ticker'].unique():
        ticker_markets = price_df[price_df['Series Ticker'] == ticker]

        if len(ticker_markets) > 0:
            total = len(ticker_markets)
            wins = (ticker_markets['Prediction Correct'] == 'CORRECT').sum()
            accuracy = (wins / total) * 100 if total > 0 else 0

            # Get category/subcategory
            category = ticker_markets['Category'].mode()[0] if len(ticker_markets) > 0 else 'Unknown'

            # Try to get subcategory from Series Title
            series_title = ticker_markets['Series Title'].mode()[0] if len(ticker_markets) > 0 else ''

            # Calculate profit
            expected_profit = calculate_expected_profit(0.91, accuracy)

            # Determine if profitable
            profitable = expected_profit > 0
            breakeven = abs(expected_profit) < 0.0050  # Within 0.5¢ of breakeven

            # Seasonality indicator
            seasonal_keywords = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAA', 'WORLD', 'CUP', 'OLYMPIC', 'EURO']
            is_seasonal = any(keyword in ticker.upper() for keyword in seasonal_keywords)

            year_round_keywords = ['BTC', 'ETH', 'SOL', 'CRYPTO', 'MENTION', 'HIGH', 'RAIN', 'TEMP', 'WEATHER', 'GDP', 'INXZ']
            is_year_round = any(keyword in ticker.upper() for keyword in year_round_keywords)

            ticker_stats.append({
                'ticker': ticker,
                'category': category,
                'series_title': series_title,
                'total_markets': total,
                'wins': wins,
                'losses': total - wins,
                'accuracy': accuracy,
                'expected_profit': expected_profit,
                'profitable': profitable,
                'breakeven': breakeven,
                'is_seasonal': is_seasonal,
                'is_year_round': is_year_round
            })

    # Convert to DataFrame
    stats_df = pd.DataFrame(ticker_stats)

    # Sort by accuracy (descending)
    stats_df = stats_df.sort_values('accuracy', ascending=False)

    # Save full list
    stats_df.to_csv('all_tickers_complete_list.csv', index=False)

    # Display full list
    print(f"{'Ticker':<30} {'Category':<20} {'Markets':>8} {'W-L':>10} {'Accuracy':>10} {'Profit/Bet':>12} {'Status':>12} {'Seasonal?':>12}")
    print("-" * 140)

    for idx, row in stats_df.iterrows():
        w_l = f"{row['wins']}-{row['losses']}"

        if row['profitable']:
            status = "✅ Profit"
        elif row['breakeven']:
            status = "⚖️  Breakeven"
        else:
            status = "❌ Loss"

        seasonal_status = "🗓️  Seasonal" if row['is_seasonal'] else ("🔄 Year-round" if row['is_year_round'] else "")

        print(f"{row['ticker']:<30} {row['category']:<20} {row['total_markets']:>8} {w_l:>10} "
              f"{row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f} {status:>12} {seasonal_status:>12}")

    print()

    # Summary by profitability
    print("=" * 100)
    print("SUMMARY BY PROFITABILITY")
    print("=" * 100)
    print()

    profitable = stats_df[stats_df['profitable']]
    breakeven_df = stats_df[stats_df['breakeven']]
    losing = stats_df[~stats_df['profitable'] & ~stats_df['breakeven']]

    print(f"PROFITABLE (>0 profit/bet): {len(profitable)} tickers")
    print(f"  Total markets: {profitable['total_markets'].sum():,}")
    print(f"  Avg accuracy: {profitable['accuracy'].mean():.1f}%")
    print(f"  Avg profit/bet: ${profitable['expected_profit'].mean():.4f}")
    print()

    print(f"BREAKEVEN (±$0.005/bet): {len(breakeven_df)} tickers")
    print(f"  Total markets: {breakeven_df['total_markets'].sum():,}")
    print(f"  Avg accuracy: {breakeven_df['accuracy'].mean():.1f}%")
    print()

    print(f"LOSING (<0 profit/bet): {len(losing)} tickers")
    print(f"  Total markets: {losing['total_markets'].sum():,}")
    print(f"  Avg accuracy: {losing['accuracy'].mean():.1f}%")
    print(f"  Avg loss/bet: ${losing['expected_profit'].mean():.4f}")
    print()

    # Summary by seasonality
    print("=" * 100)
    print("SUMMARY BY SEASONALITY")
    print("=" * 100)
    print()

    seasonal = stats_df[stats_df['is_seasonal']]
    year_round = stats_df[stats_df['is_year_round']]
    other = stats_df[~stats_df['is_seasonal'] & ~stats_df['is_year_round']]

    print(f"SEASONAL ({len(seasonal)} tickers): NFL, NBA, MLB, NCAA, etc.")
    print(f"  Profitable: {seasonal['profitable'].sum()} ({seasonal['profitable'].sum()/len(seasonal)*100:.1f}%)")
    print(f"  Avg accuracy: {seasonal['accuracy'].mean():.1f}%")
    print()

    print(f"YEAR-ROUND ({len(year_round)} tickers): Crypto, weather, mentions, etc.")
    print(f"  Profitable: {year_round['profitable'].sum()} ({year_round['profitable'].sum()/len(year_round)*100:.1f}%)")
    print(f"  Avg accuracy: {year_round['accuracy'].mean():.1f}%")
    print()

    print(f"OTHER ({len(other)} tickers)")
    print(f"  Profitable: {other['profitable'].sum()} ({other['profitable'].sum()/len(other)*100:.1f}%)")
    print(f"  Avg accuracy: {other['accuracy'].mean():.1f}%")
    print()

    # Breakdown by category
    print("=" * 100)
    print("BREAKDOWN BY CATEGORY")
    print("=" * 100)
    print()

    category_breakdown = stats_df.groupby('category').agg({
        'total_markets': 'sum',
        'wins': 'sum',
        'profitable': 'sum',
        'ticker': 'count'
    }).rename(columns={'ticker': 'num_tickers'}).sort_values('total_markets', ascending=False)

    category_breakdown['accuracy'] = (category_breakdown['wins'] / category_breakdown['total_markets'] * 100).round(1)

    print(f"{'Category':<30} {'Tickers':>10} {'Markets':>10} {'Profitable':>12} {'Accuracy':>10}")
    print("-" * 100)

    for category, row in category_breakdown.iterrows():
        print(f"{category:<30} {int(row['num_tickers']):>10} {int(row['total_markets']):>10} "
              f"{int(row['profitable']):>12} {row['accuracy']:>9.1f}%")

    print()

    # Recommended tickers for year-round trading
    print("=" * 120)
    print("RECOMMENDED FOR YEAR-ROUND TRADING (profitable + likely active now)")
    print("=" * 120)
    print()

    # Crypto, weather, mentions, stock indices (year-round)
    year_round_profitable = stats_df[
        stats_df['is_year_round'] & stats_df['profitable']
    ].sort_values('expected_profit', ascending=False)

    if len(year_round_profitable) > 0:
        print("YEAR-ROUND PROFITABLE:")
        print()
        print(f"{'Ticker':<30} {'Category':<20} {'Markets':>8} {'Accuracy':>10} {'Profit/Bet':>12}")
        print("-" * 120)

        for idx, row in year_round_profitable.iterrows():
            print(f"{row['ticker']:<30} {row['category']:<20} {row['total_markets']:>8} "
                  f"{row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f}")
    else:
        print("No year-round profitable tickers found")

    print()

    # Best seasonal tickers (for when they're active)
    print("=" * 120)
    print("BEST SEASONAL TICKERS (for when they're in season)")
    print("=" * 120)
    print()

    seasonal_profitable = stats_df[
        stats_df['is_seasonal'] & stats_df['profitable']
    ].sort_values('expected_profit', ascending=False)

    # Group by sport
    for sport in ['NBA', 'NFL', 'NCAA', 'MLB', 'NHL']:
        sport_tickers = seasonal_profitable[
            seasonal_profitable['ticker'].str.contains(sport, case=False, na=False)
        ]

        if len(sport_tickers) > 0:
            print(f"\n{sport}:")
            for idx, row in sport_tickers.iterrows():
                print(f"  {row['ticker']:<28} {row['accuracy']:>6.1f}%, ${row['expected_profit']:>7.4f}/bet ({row['total_markets']:>3} markets)")

    print()

    # Tickers to consider even if below 91%
    print("=" * 120)
    print("MARGINAL TICKERS (85-91% accuracy - consider if high volume or strategic)")
    print("=" * 120)
    print()

    marginal = stats_df[
        (stats_df['accuracy'] >= 85) &
        (stats_df['accuracy'] < 91) &
        (stats_df['total_markets'] >= 20)  # Only if decent sample size
    ].sort_values('accuracy', ascending=False)

    if len(marginal) > 0:
        print(f"{'Ticker':<30} {'Category':<20} {'Markets':>8} {'Accuracy':>10} {'Loss/Bet':>12} {'Note':>30}")
        print("-" * 140)

        for idx, row in marginal.iterrows():
            note = ""
            if row['accuracy'] >= 89:
                note = "Close to breakeven"
            elif row['total_markets'] >= 50:
                note = "High volume"

            print(f"{row['ticker']:<30} {row['category']:<20} {row['total_markets']:>8} "
                  f"{row['accuracy']:>9.1f}% ${row['expected_profit']:>10.4f} {note:>30}")
    else:
        print("No marginal tickers with sufficient sample size")

    print()

    print("✅ Saved complete list to: all_tickers_complete_list.csv")
    print()

    # Final recommendations
    print("=" * 100)
    print("FINAL RECOMMENDATIONS FOR BOT CONFIGURATION")
    print("=" * 100)
    print()

    print("STRATEGY 1: CONSERVATIVE (profitable only)")
    print(f"  - {len(profitable)} tickers")
    print(f"  - Avg profit: ${profitable['expected_profit'].mean():.4f}/bet")
    print(f"  - Avg accuracy: {profitable['accuracy'].mean():.1f}%")
    print()

    print("STRATEGY 2: AGGRESSIVE (include breakeven + high volume)")
    aggressive = stats_df[
        (stats_df['profitable'] | stats_df['breakeven']) |
        ((stats_df['accuracy'] >= 88) & (stats_df['total_markets'] >= 50))
    ]
    print(f"  - {len(aggressive)} tickers")
    print(f"  - Avg profit: ${aggressive['expected_profit'].mean():.4f}/bet")
    print(f"  - Avg accuracy: {aggressive['accuracy'].mean():.1f}%")
    print()

    print("STRATEGY 3: YEAR-ROUND FOCUS (non-seasonal profitable)")
    year_round_focus = stats_df[
        stats_df['is_year_round'] & stats_df['profitable']
    ]
    print(f"  - {len(year_round_focus)} tickers")
    print(f"  - Avg profit: ${year_round_focus['expected_profit'].mean():.4f}/bet")
    print(f"  - Guarantees daily opportunities")
    print()

if __name__ == "__main__":
    main()
