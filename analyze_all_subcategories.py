"""
Analyze accuracy for EVERY hierarchical sub-category in the backtest data.
No filtering - show all sub-categories regardless of accuracy or sample size.
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory


def analyze_all_subcategories():
    """Analyze ALL hierarchical sub-categories - no filters."""

    print("Loading backtest data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    print(f"Total markets in backtest: {len(df):,}")
    print()

    # Map each row to hierarchical sub-categories
    df['Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[0],
        axis=1
    )
    df['Sub_Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[1],
        axis=1
    )

    # Create full hierarchical path
    df['Hierarchical_Path'] = df.apply(
        lambda row: f"{row['Category']} > {row['Sub_Category']}" if pd.isna(row['Sub_Sub_Category'])
                    else f"{row['Category']} > {row['Sub_Category']} > {row['Sub_Sub_Category']}",
        axis=1
    )

    # Calculate accuracy by hierarchical path
    results = []
    for path in sorted(df['Hierarchical_Path'].unique()):
        path_df = df[df['Hierarchical_Path'] == path]
        total_markets = len(path_df)
        correct = (path_df['Prediction Correct'] == 'CORRECT').sum()
        accuracy = correct / total_markets if total_markets > 0 else 0

        # Calculate EV with 91.5¢ representative price
        avg_price = 0.915
        profit_if_win = (1.00 - avg_price) * 100  # in cents
        loss_if_lose = avg_price * 100  # in cents
        fee = 0.07 * avg_price * (1 - avg_price) * 100  # in cents
        ev_per_contract = (accuracy * profit_if_win) - ((1 - accuracy) * loss_if_lose) - fee

        results.append({
            'Hierarchical_Path': path,
            'Total_Markets': total_markets,
            'Correct': correct,
            'Wrong': total_markets - correct,
            'Accuracy': accuracy,
            'EV_per_Contract': ev_per_contract,
            'Profitable': 'Yes' if ev_per_contract > 0 else 'No'
        })

    # Convert to DataFrame and sort by total markets (descending)
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Total_Markets', ascending=False)

    print("=" * 120)
    print("ALL HIERARCHICAL SUB-CATEGORIES (sorted by market count)")
    print("=" * 120)
    print(f"\nTotal unique sub-categories: {len(results_df)}\n")

    # Print summary stats first
    print(f"Summary Statistics:")
    print(f"  Total markets: {results_df['Total_Markets'].sum():,}")
    print(f"  Sub-categories with 90%+ accuracy: {(results_df['Accuracy'] >= 0.90).sum()}")
    print(f"  Sub-categories with 20+ markets: {(results_df['Total_Markets'] >= 20).sum()}")
    print(f"  Sub-categories with 90%+ accuracy AND 20+ markets: {((results_df['Accuracy'] >= 0.90) & (results_df['Total_Markets'] >= 20)).sum()}")
    print(f"  Profitable sub-categories (all): {(results_df['EV_per_Contract'] > 0).sum()}")
    print()

    # Save to CSV
    output_file = 'all_subcategories_analysis.csv'
    results_df.to_csv(output_file, index=False)
    print(f"Full analysis saved to {output_file}")
    print()

    # Print top 50 by market count for quick review
    print("=" * 120)
    print("TOP 50 SUB-CATEGORIES BY MARKET COUNT")
    print("=" * 120)
    print()

    for idx, row in results_df.head(50).iterrows():
        profitable_flag = "✓" if row['Profitable'] == 'Yes' else "✗"
        print(f"{row['Hierarchical_Path']}")
        print(f"  Markets: {row['Total_Markets']:,} | Accuracy: {row['Accuracy']:.1%} ({row['Correct']}/{row['Total_Markets']}) | EV: {row['EV_per_Contract']:.2f}¢ [{profitable_flag}]")
        print()

    return results_df


if __name__ == "__main__":
    analyze_all_subcategories()
