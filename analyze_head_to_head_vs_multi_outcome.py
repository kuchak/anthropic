"""
Analyze head-to-head vs multi-outcome markets in the Kalshi backtest data.

Determines if markets are:
- Head-to-head: 2 outcomes per event
- Multi-outcome: 3+ outcomes per event

Shows accuracy separately for each type to determine if we should exclude multi-outcome markets.
"""

import pandas as pd
from collections import defaultdict
import re

def extract_event_ticker(ticker):
    """
    Extract event ticker from market ticker.

    Format: KXSERIESNAME-26FEB14-OUTCOME -> KXSERIESNAME-26FEB14

    Examples:
    - KXBILLBOARDRUNNERUPSONG-26FEB14-MAN -> KXBILLBOARDRUNNERUPSONG-26FEB14
    - KXATPMATCH-26FEB13LMU -> KXATPMATCH-26FEB13
    """
    # Split on hyphen
    parts = ticker.split('-')

    if len(parts) < 2:
        return None

    # Series ticker is first part
    series = parts[0]

    # Date portion is in the second part
    # Look for date pattern like 26FEB14, 26FEB13, etc.
    date_match = re.search(r'\d{2}[A-Z]{3}\d{2}', parts[1])
    if date_match:
        date = date_match.group()
        return f"{series}-{date}"

    # Some tickers may have date in different format
    # Try to extract any alphanumeric portion that looks like a date
    if len(parts[1]) >= 7:
        # Take first 7-9 characters as potential date identifier
        return f"{series}-{parts[1][:9]}"

    return f"{series}-{parts[1]}"

def main():
    print("=" * 120)
    print("HEAD-TO-HEAD vs MULTI-OUTCOME MARKET ANALYSIS")
    print("=" * 120)
    print()

    # Load the backtest CSV
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    print(f"Total markets in backtest: {len(df):,}")
    print()

    # Filter to 90-93¢ range
    price_df = df[
        (df['First Touch Price (¢)'] >= 90) &
        (df['First Touch Price (¢)'] < 93)
    ].copy()

    print(f"Markets in 90-93¢ range: {len(price_df):,}")
    print()

    # Extract event ticker for each market
    price_df['Event Ticker'] = price_df['Ticker'].apply(extract_event_ticker)

    # Count outcomes per event
    event_outcome_counts = price_df['Event Ticker'].value_counts()

    # Classify events as head-to-head or multi-outcome
    price_df['Market Type'] = price_df['Event Ticker'].apply(
        lambda x: 'Head-to-Head (2)' if event_outcome_counts.get(x, 0) == 2 else
                  f'Multi-Outcome ({event_outcome_counts.get(x, 0)}+)' if event_outcome_counts.get(x, 0) >= 3 else
                  'Single Outcome'
    )

    print("=" * 120)
    print("OVERALL BREAKDOWN")
    print("=" * 120)
    print()

    market_type_counts = price_df['Market Type'].value_counts()
    print("Market Distribution:")
    for market_type, count in market_type_counts.items():
        pct = count / len(price_df) * 100
        print(f"  {market_type}: {count:,} markets ({pct:.1f}%)")
    print()

    # Calculate accuracy by market type
    print("=" * 120)
    print("ACCURACY BY MARKET TYPE")
    print("=" * 120)
    print()

    for market_type in sorted(price_df['Market Type'].unique()):
        subset = price_df[price_df['Market Type'] == market_type]
        total = len(subset)
        correct = (subset['Prediction Correct'] == 'CORRECT').sum()
        accuracy = (correct / total * 100) if total > 0 else 0

        print(f"{market_type}:")
        print(f"  Total: {total:,} markets")
        print(f"  Correct: {correct:,}")
        print(f"  Accuracy: {accuracy:.2f}%")
        print()

    # Break down by series ticker
    print("=" * 120)
    print("ACCURACY BY SERIES TICKER - HEAD-TO-HEAD vs MULTI-OUTCOME")
    print("=" * 120)
    print()

    results = []

    for series_ticker in sorted(price_df['Series Ticker'].unique()):
        series_data = price_df[price_df['Series Ticker'] == series_ticker]

        # Head-to-head
        h2h_data = series_data[series_data['Market Type'] == 'Head-to-Head (2)']
        h2h_total = len(h2h_data)
        h2h_correct = (h2h_data['Prediction Correct'] == 'CORRECT').sum()
        h2h_accuracy = (h2h_correct / h2h_total * 100) if h2h_total > 0 else 0

        # Multi-outcome (3+)
        multi_data = series_data[series_data['Market Type'].str.contains('Multi-Outcome')]
        multi_total = len(multi_data)
        multi_correct = (multi_data['Prediction Correct'] == 'CORRECT').sum()
        multi_accuracy = (multi_correct / multi_total * 100) if multi_total > 0 else 0

        # Single outcome
        single_data = series_data[series_data['Market Type'] == 'Single Outcome']
        single_total = len(single_data)
        single_correct = (single_data['Prediction Correct'] == 'CORRECT').sum()
        single_accuracy = (single_correct / single_total * 100) if single_total > 0 else 0

        # Overall
        overall_total = len(series_data)
        overall_correct = (series_data['Prediction Correct'] == 'CORRECT').sum()
        overall_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0

        results.append({
            'Series Ticker': series_ticker,
            'H2H Markets': h2h_total,
            'H2H Accuracy': h2h_accuracy,
            'Multi Markets': multi_total,
            'Multi Accuracy': multi_accuracy,
            'Single Markets': single_total,
            'Single Accuracy': single_accuracy,
            'Total Markets': overall_total,
            'Overall Accuracy': overall_accuracy
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Total Markets', ascending=False)

    # Display top series tickers
    print(f"{'Series Ticker':<30} {'H2H':<15} {'Multi':<15} {'Single':<15} {'Overall':<15}")
    print(f"{'':30} {'Markets | Acc%':<15} {'Markets | Acc%':<15} {'Markets | Acc%':<15} {'Markets | Acc%':<15}")
    print("-" * 120)

    for _, row in results_df.iterrows():
        h2h_str = f"{row['H2H Markets']:4} | {row['H2H Accuracy']:5.1f}%" if row['H2H Markets'] > 0 else "   - |     -"
        multi_str = f"{row['Multi Markets']:4} | {row['Multi Accuracy']:5.1f}%" if row['Multi Markets'] > 0 else "   - |     -"
        single_str = f"{row['Single Markets']:4} | {row['Single Accuracy']:5.1f}%" if row['Single Markets'] > 0 else "   - |     -"
        overall_str = f"{row['Total Markets']:4} | {row['Overall Accuracy']:5.1f}%"

        print(f"{row['Series Ticker']:<30} {h2h_str:<15} {multi_str:<15} {single_str:<15} {overall_str:<15}")

    print()

    # Summary statistics
    print("=" * 120)
    print("SUMMARY STATISTICS")
    print("=" * 120)
    print()

    # Overall accuracy comparison
    h2h_all = price_df[price_df['Market Type'] == 'Head-to-Head (2)']
    multi_all = price_df[price_df['Market Type'].str.contains('Multi-Outcome')]

    if len(h2h_all) > 0:
        h2h_acc = (h2h_all['Prediction Correct'] == 'CORRECT').sum() / len(h2h_all) * 100
        print(f"Head-to-Head (2 outcomes): {len(h2h_all):,} markets, {h2h_acc:.2f}% accuracy")

    if len(multi_all) > 0:
        multi_acc = (multi_all['Prediction Correct'] == 'CORRECT').sum() / len(multi_all) * 100
        print(f"Multi-Outcome (3+ outcomes): {len(multi_all):,} markets, {multi_acc:.2f}% accuracy")

        # Calculate accuracy delta
        if len(h2h_all) > 0:
            delta = h2h_acc - multi_acc
            print()
            print(f"Accuracy difference: {delta:+.2f} percentage points (H2H vs Multi)")
            print()

            if delta > 3:
                print("✅ RECOMMENDATION: Head-to-head markets perform significantly better.")
                print("   Consider EXCLUDING multi-outcome markets or trading them with lower confidence.")
            elif delta < -3:
                print("⚠️  CAUTION: Multi-outcome markets perform significantly better.")
                print("   This is unexpected - review data quality.")
            else:
                print("✅ CONCLUSION: No significant difference between head-to-head and multi-outcome markets.")
                print("   Both market types can be traded with equal confidence.")

    print()

    # Save detailed results
    price_df.to_csv('backtest_with_market_types.csv', index=False)
    print("✅ Saved detailed analysis to: backtest_with_market_types.csv")

    results_df.to_csv('accuracy_by_market_type_and_ticker.csv', index=False)
    print("✅ Saved ticker breakdown to: accuracy_by_market_type_and_ticker.csv")
    print()

if __name__ == "__main__":
    main()
