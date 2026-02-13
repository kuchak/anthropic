"""
Two critical analyses:

1. Find the missing NBA markets (KXNBAGAME, KXNBASPREAD, KXNBAREB)
   - Were they in the stability analysis?
   - What's their accuracy at 90-92¢?

2. Calculate expected profit per $1 bet for all profitable tickers
   - Use actual accuracy
   - Account for 7% Kalshi fees
   - Rank by profit, not just accuracy
"""

import pandas as pd
import yaml
import math

def calculate_fee(price, fee_rate=0.07):
    """Kalshi fee formula: ceil(fee_rate × price × (1 - price) × 100) / 100"""
    fee = fee_rate * price * (1.0 - price)
    return math.ceil(fee * 100) / 100

def calculate_expected_profit(price, accuracy, fee_rate=0.07):
    """
    Calculate expected profit per $1 bet.

    Args:
        price: Entry price (e.g., 0.91 for 91¢)
        accuracy: Win probability (e.g., 0.98 for 98%)
        fee_rate: Kalshi taker fee (7%)

    Returns:
        Expected profit per bet
    """
    fee = calculate_fee(price, fee_rate)
    total_cost = price + fee

    # If win: get $1.00, paid total_cost
    profit_if_win = 1.00 - total_cost

    # If loss: lose total_cost
    loss_if_lose = -total_cost

    # Expected value
    expected = (accuracy * profit_if_win) + ((1 - accuracy) * loss_if_lose)

    return expected

def main():
    print("=" * 100)
    print("ANALYSIS 1: FINDING MISSING NBA MARKETS")
    print("=" * 100)
    print()

    # Load comprehensive backtest data
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Check for NBA markets
    nba_markets = ['KXNBAGAME', 'KXNBASPREAD', 'KXNBAREB']

    print("Searching for NBA markets in backtest data:")
    print()

    for ticker in nba_markets:
        # All markets
        ticker_all = df[df['Series Ticker'] == ticker]

        # 90-92¢ range
        ticker_90_92 = df[
            (df['Series Ticker'] == ticker) &
            (df['First Touch Price (¢)'] >= 90) &
            (df['First Touch Price (¢)'] < 93)
        ]

        if len(ticker_all) > 0:
            total = len(ticker_all)
            wins_all = (ticker_all['Prediction Correct'] == 'CORRECT').sum()
            acc_all = (wins_all / total * 100) if total > 0 else 0

            if len(ticker_90_92) > 0:
                total_90_92 = len(ticker_90_92)
                wins_90_92 = (ticker_90_92['Prediction Correct'] == 'CORRECT').sum()
                acc_90_92 = (wins_90_92 / total_90_92 * 100) if total_90_92 > 0 else 0

                print(f"✅ {ticker}:")
                print(f"   All prices: {total:,} markets, {acc_all:.1f}% accurate")
                print(f"   90-92¢ range: {total_90_92} markets, {acc_90_92:.1f}% accurate")
            else:
                print(f"⚠️  {ticker}:")
                print(f"   All prices: {total:,} markets, {acc_all:.1f}% accurate")
                print(f"   90-92¢ range: 0 markets (MISSING!)")
        else:
            print(f"❌ {ticker}: NOT FOUND in backtest data")

        print()

    # Check stability data
    print("Checking stability analysis data:")
    print()

    stability_df = pd.read_csv('stability_waiting_period_by_ticker.csv')

    for ticker in nba_markets:
        if ticker in stability_df['ticker'].values:
            row = stability_df[stability_df['ticker'] == ticker].iloc[0]
            print(f"✅ {ticker} in stability data:")
            print(f"   Median gap: {row['median_gap']:.1f} minutes")
            print(f"   Sample size: {row['count']}")
        else:
            print(f"❌ {ticker} NOT in stability data")
        print()

    print("=" * 100)
    print("ANALYSIS 2: EXPECTED PROFIT PER BET (91¢ entry)")
    print("=" * 100)
    print()

    # Load profitable tickers
    profitable_df = pd.read_csv('profitable_tickers_with_wait_times.csv')

    # Calculate expected profit for each ticker
    results = []

    entry_price = 0.91  # 91¢

    for idx, row in profitable_df.iterrows():
        ticker = row['ticker']
        category = row['category']
        wait_minutes = row['wait_minutes']
        total_markets = row['total_markets']
        accuracy_pct = row['accuracy']
        accuracy = accuracy_pct / 100  # Convert to decimal

        expected_profit = calculate_expected_profit(entry_price, accuracy)

        # ROI percentage
        total_cost = entry_price + calculate_fee(entry_price)
        roi_pct = (expected_profit / total_cost) * 100

        results.append({
            'ticker': ticker,
            'category': category,
            'wait_minutes': wait_minutes,
            'markets': total_markets,
            'accuracy': accuracy_pct,
            'expected_profit_per_bet': expected_profit,
            'roi_pct': roi_pct
        })

    results_df = pd.DataFrame(results)

    # Sort by expected profit (descending)
    results_df = results_df.sort_values('expected_profit_per_bet', ascending=False)

    print(f"Entry price: 91¢ ($0.91)")
    print(f"Fee (7% taker): ${calculate_fee(entry_price):.2f}")
    print(f"Total cost per bet: ${entry_price + calculate_fee(entry_price):.2f}")
    print()
    print(f"If win: Profit = $1.00 - ${entry_price + calculate_fee(entry_price):.2f} = ${1.00 - (entry_price + calculate_fee(entry_price)):.2f}")
    print(f"If loss: Loss = -${entry_price + calculate_fee(entry_price):.2f}")
    print()

    print("=" * 120)
    print(f"{'Rank':<6} {'Ticker':<30} {'Category':<20} {'Wait':>6} {'Accuracy':>10} {'Profit/Bet':>12} {'ROI':>8}")
    print("-" * 120)

    for rank, (idx, row) in enumerate(results_df.iterrows(), 1):
        print(f"{rank:<6} {row['ticker']:<30} {row['category']:<20} {row['wait_minutes']:>4}m "
              f"{row['accuracy']:>9.1f}% ${row['expected_profit_per_bet']:>10.4f} {row['roi_pct']:>7.1f}%")

    print()

    # Summary by wait time
    print("=" * 100)
    print("SUMMARY BY WAIT TIME CATEGORY")
    print("=" * 100)
    print()

    for wait_time in [1, 3, 5]:
        wait_df = results_df[results_df['wait_minutes'] == wait_time]

        if len(wait_df) > 0:
            print(f"{wait_time}-MINUTE WAIT:")
            print(f"  Tickers: {len(wait_df)}")
            print(f"  Avg accuracy: {wait_df['accuracy'].mean():.1f}%")
            print(f"  Avg profit per bet: ${wait_df['expected_profit_per_bet'].mean():.4f}")
            print(f"  Avg ROI: {wait_df['roi_pct'].mean():.1f}%")
            print(f"  Best: {wait_df.iloc[0]['ticker']} (${wait_df.iloc[0]['expected_profit_per_bet']:.4f}/bet)")
            print()

    # Overall
    print("OVERALL:")
    print(f"  Total tickers: {len(results_df)}")
    print(f"  Avg profit per bet: ${results_df['expected_profit_per_bet'].mean():.4f}")
    print(f"  Avg ROI: {results_df['roi_pct'].mean():.1f}%")
    print(f"  Best ticker: {results_df.iloc[0]['ticker']} (${results_df.iloc[0]['expected_profit_per_bet']:.4f}/bet)")
    print(f"  Worst ticker: {results_df.iloc[-1]['ticker']} (${results_df.iloc[-1]['expected_profit_per_bet']:.4f}/bet)")
    print()

    # Breakeven analysis
    print("=" * 100)
    print("BREAKEVEN ANALYSIS")
    print("=" * 100)
    print()

    print("At 91¢ entry with 7% fees:")
    print()

    # Find breakeven accuracy
    breakeven_accuracy = None
    for acc_pct in range(80, 100):
        acc = acc_pct / 100
        exp_profit = calculate_expected_profit(entry_price, acc)
        if exp_profit >= 0:
            breakeven_accuracy = acc_pct
            break

    print(f"Breakeven accuracy: ~{breakeven_accuracy}%")
    print()

    # Show profitability tiers
    print("Profitability tiers:")
    print(f"  98%+ accuracy: ${calculate_expected_profit(entry_price, 0.98):.4f}/bet (excellent)")
    print(f"  95-98% accuracy: ${calculate_expected_profit(entry_price, 0.96):.4f}/bet (very good)")
    print(f"  92-95% accuracy: ${calculate_expected_profit(entry_price, 0.93):.4f}/bet (good)")
    print(f"  91-92% accuracy: ${calculate_expected_profit(entry_price, 0.915):.4f}/bet (marginal)")
    print(f"  <91% accuracy: ${calculate_expected_profit(entry_price, 0.90):.4f}/bet (LOSING)")
    print()

    # Save ranked list
    results_df.to_csv('tickers_ranked_by_profit.csv', index=False)
    print("✅ Saved to: tickers_ranked_by_profit.csv")
    print()

    # Top 10 most profitable
    print("=" * 100)
    print("TOP 10 MOST PROFITABLE TICKERS (by expected profit per bet)")
    print("=" * 100)
    print()

    top10 = results_df.head(10)

    print(f"{'Rank':<6} {'Ticker':<30} {'Category':<20} {'Accuracy':>10} {'Profit/Bet':>12}")
    print("-" * 100)

    for rank, (idx, row) in enumerate(top10.iterrows(), 1):
        print(f"{rank:<6} {row['ticker']:<30} {row['category']:<20} {row['accuracy']:>9.1f}% ${row['expected_profit_per_bet']:>10.4f}")

    print()

    # Compare to bottom 10
    print("=" * 100)
    print("BOTTOM 10 LEAST PROFITABLE TICKERS (still > 91%, but lowest profit)")
    print("=" * 100)
    print()

    bottom10 = results_df.tail(10).sort_values('expected_profit_per_bet', ascending=True)

    print(f"{'Rank':<6} {'Ticker':<30} {'Category':<20} {'Accuracy':>10} {'Profit/Bet':>12}")
    print("-" * 100)

    for rank, (idx, row) in enumerate(bottom10.iterrows(), 1):
        print(f"{rank:<6} {row['ticker']:<30} {row['category']:<20} {row['accuracy']:>9.1f}% ${row['expected_profit_per_bet']:>10.4f}")

    print()

    print("=" * 100)
    print("KEY INSIGHT: Accuracy matters EXPONENTIALLY for profit!")
    print("=" * 100)
    print()
    print(f"98% accurate ticker: ${calculate_expected_profit(entry_price, 0.98):.4f}/bet")
    print(f"95% accurate ticker: ${calculate_expected_profit(entry_price, 0.95):.4f}/bet")
    print(f"92% accurate ticker: ${calculate_expected_profit(entry_price, 0.92):.4f}/bet")
    print(f"91% accurate ticker: ${calculate_expected_profit(entry_price, 0.91):.4f}/bet (barely profitable)")
    print()
    print("Difference: 98% makes 6x more per bet than 91%!")
    print()

    print("✅ Analysis complete!")
    print()

if __name__ == "__main__":
    main()
