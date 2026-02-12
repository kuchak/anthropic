"""
Export detailed market-by-market data for top 5 sub-categories by sample size.
Includes: Ticker, Market Question, First Touch Price, Settlement Date, Result
"""

import pandas as pd
from map_kalshi_subcategories import map_to_subcategory


def export_top5_markets():
    """Export individual markets for top 5 sub-categories by sample size."""

    print("Loading backtest data...")
    df = pd.read_csv('comprehensive_crossed_90_detailed.csv')

    # Map to hierarchical sub-categories
    df['Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[0],
        axis=1
    )
    df['Sub_Sub_Category'] = df.apply(
        lambda row: map_to_subcategory(row['Category'], row['Series Ticker'], row['Series Title'])[1],
        axis=1
    )

    df['Hierarchical_Path'] = df.apply(
        lambda row: f"{row['Category']} > {row['Sub_Category']}" if pd.isna(row['Sub_Sub_Category'])
                    else f"{row['Category']} > {row['Sub_Category']} > {row['Sub_Sub_Category']}",
        axis=1
    )

    # Count markets per sub-category
    subcategory_counts = df.groupby('Hierarchical_Path').size().reset_index(name='Market_Count')
    subcategory_counts = subcategory_counts.sort_values('Market_Count', ascending=False)

    # Get top 5
    top5 = subcategory_counts.head(5)

    print("=" * 100)
    print("TOP 5 SUB-CATEGORIES BY SAMPLE SIZE")
    print("=" * 100)
    for idx, row in top5.iterrows():
        print(f"{idx+1}. {row['Hierarchical_Path']}: {row['Market_Count']:,} markets")
    print()

    # Filter data for top 5 and prepare export
    top5_paths = set(top5['Hierarchical_Path'].values)
    export_df = df[df['Hierarchical_Path'].isin(top5_paths)].copy()

    # Parse settlement date from Market Close Time
    export_df['Settlement_Date'] = pd.to_datetime(export_df['Market Close Time'], format='ISO8601').dt.strftime('%Y-%m-%d')

    # Select and rename columns for export
    export_columns = {
        'Hierarchical_Path': 'Sub_Category',
        'Ticker': 'Kalshi_Ticker',
        'Title': 'Market_Question',
        'First Touch Price (¢)': 'Price_At_85_Plus',
        'Settlement_Date': 'Settlement_Date',
        'Prediction Correct': 'Result',
        'Settlement (¢)': 'Settlement_Value',
        'First Touch Time': 'First_Touch_Time',
        'Series Ticker': 'Series_Ticker',
        'Series Title': 'Series_Title'
    }

    export_df = export_df[list(export_columns.keys())].copy()
    export_df.columns = list(export_columns.values())

    # Sort by sub-category and settlement date
    export_df = export_df.sort_values(['Sub_Category', 'Settlement_Date'])

    # Save to CSV
    output_file = 'top5_subcategories_individual_markets.csv'
    export_df.to_csv(output_file, index=False)

    print(f"Exported {len(export_df):,} markets to {output_file}")
    print()

    # Print summary by sub-category
    print("=" * 100)
    print("BREAKDOWN BY SUB-CATEGORY")
    print("=" * 100)
    for path in sorted(top5_paths):
        sub_df = export_df[export_df['Sub_Category'] == path]
        correct = (sub_df['Result'] == 'CORRECT').sum()
        wrong = (sub_df['Result'] == 'WRONG').sum()
        accuracy = correct / len(sub_df) * 100
        print(f"\n{path}")
        print(f"  Total markets: {len(sub_df):,}")
        print(f"  Correct: {correct:,} | Wrong: {wrong:,}")
        print(f"  Accuracy: {accuracy:.1f}%")
        print(f"  Date range: {sub_df['Settlement_Date'].min()} to {sub_df['Settlement_Date'].max()}")
        print(f"  Avg price at 85%+: {sub_df['Price_At_85_Plus'].mean():.1f}¢")

    return export_df


if __name__ == "__main__":
    export_top5_markets()
