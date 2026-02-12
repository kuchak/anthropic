"""
Map CSV data to Kalshi's actual hierarchical sub-category structure.

For Sports: 2-layer hierarchy (Sport Type > Specific League/Tournament)
For Other Categories: 1-layer hierarchy (Category > Sub-Category)
"""

import pandas as pd
import re
from collections import defaultdict


def map_to_subcategory(category, series_ticker, series_title):
    """
    Map a series to its hierarchical sub-category structure.

    Returns tuple: (sub_category, sub_sub_category) where sub_sub_category may be None
    """

    # ENTERTAINMENT/CULTURE SUB-CATEGORIES
    if category == "Entertainment":
        # Music charts (Billboard, Spotify)
        if any(x in series_ticker for x in ['BILLBOARD', 'SPOTIFY']):
            return ("Music charts", None)

        # Movies (Netflix, Rotten Tomatoes)
        if 'NETFLIX' in series_ticker:
            return ("Movies", None)

        # Awards
        if any(x in series_ticker for x in ['AWARD', 'DGA', 'GRAMMYS']):
            return ("Awards", None)

        # Television
        if 'SURVIVOR' in series_ticker:
            return ("Television", None)

        # Apps
        if 'APPRANK' in series_ticker:
            return ("Apps", None)

        return ("Other", None)

    # SPORTS SUB-CATEGORIES (2-LAYER HIERARCHY)
    elif category == "Sports":
        ticker = series_ticker.upper()
        title = series_title.upper()

        # TENNIS (2nd level: ATP, WTA, Grand Slams, Challenger, United Cup)
        if any(x in ticker for x in ['ATP', 'WTA', 'FOMEN', 'FOWOMEN', 'TENNIS', 'UNITEDCUP']):
            if 'ATPCHALLENGER' in ticker:
                return ("Tennis", "ATP Challenger")
            elif 'ATP' in ticker:
                # Check for specific tournaments
                if 'ATPMIA' in ticker or 'MIAMI' in title:
                    return ("Tennis", "ATP Miami")
                elif 'ATPMAD' in ticker or 'MADRID' in title:
                    return ("Tennis", "ATP Madrid")
                elif 'ATPIT' in ticker or 'ITALIAN' in title:
                    return ("Tennis", "ATP Italian Open")
                elif 'ATPAMT' in ticker:
                    return ("Tennis", "ATP Other")
                else:
                    return ("Tennis", "ATP")
            elif 'WTACHALLENGER' in ticker:
                return ("Tennis", "WTA Challenger")
            elif 'WTA' in ticker:
                # Check for specific tournaments
                if 'WTAMIA' in ticker or 'MIAMI' in title:
                    return ("Tennis", "WTA Miami")
                elif 'WTAMAD' in ticker or 'MADRID' in title:
                    return ("Tennis", "WTA Madrid")
                elif 'WTAIT' in ticker or 'ITALIAN' in title:
                    return ("Tennis", "WTA Italian Open")
                elif 'WTAATX' in ticker:
                    return ("Tennis", "WTA ATX Open")
                elif 'WTAMOA' in ticker:
                    return ("Tennis", "WTA Merida Open")
                else:
                    return ("Tennis", "WTA")
            elif 'FOMEN' in ticker or "FRENCH OPEN MEN" in title:
                return ("Tennis", "French Open Men's Singles")
            elif 'FOWOMEN' in ticker or "FRENCH OPEN WOMEN" in title:
                return ("Tennis", "French Open Women's Singles")
            elif 'UNITEDCUP' in ticker:
                return ("Tennis", "United Cup")
            elif 'TENNISEXHIBITION' in ticker:
                return ("Tennis", "Exhibition")
            else:
                return ("Tennis", "Other")

        # BASKETBALL (2nd level: NBA, NCAA, International leagues)
        elif any(x in ticker for x in ['NBA', 'BASKETBALL', 'NCAAMB', 'UNRIVALED']):
            if 'NBA' in ticker and 'NCAA' not in ticker:
                return ("Basketball", "NBA")
            elif 'NCAAMB' in ticker or 'COLLEGE BASKETBALL' in title:
                return ("Basketball", "NCAA Men's Basketball")
            elif 'EUROLEAGUE' in ticker:
                return ("Basketball", "Euroleague")
            elif 'EUROCUP' in ticker:
                return ("Basketball", "Eurocup")
            elif 'KBL' in ticker:
                return ("Basketball", "Korea KBL")
            elif 'CBA' in ticker:
                return ("Basketball", "Chinese Basketball Association")
            elif 'ARGLNB' in ticker:
                return ("Basketball", "Argentina LNB")
            elif 'JBLEAGUE' in ticker:
                return ("Basketball", "Japan B League")
            elif 'LNBELITE' in ticker:
                return ("Basketball", "France LNB Elite")
            elif 'NBL' in ticker:
                return ("Basketball", "NBL")
            elif 'UNRIVALED' in ticker:
                return ("Basketball", "Unrivaled")
            elif 'WNBA' in ticker:
                return ("Basketball", "WNBA")
            elif 'FIBA' in ticker:
                return ("Basketball", "FIBA")
            else:
                return ("Basketball", "Other")

        # AMERICAN FOOTBALL (2nd level: NFL, NCAA Football)
        elif any(x in ticker for x in ['NFL', 'NCAAF']):
            if 'NFL' in ticker and 'NCAA' not in ticker:
                return ("Football", "NFL")
            elif 'NCAAF' in ticker:
                return ("Football", "NCAA Football")
            else:
                return ("Football", "Other")

        # SOCCER/FOOTBALL (2nd level: EPL, La Liga, Bundesliga, etc.)
        elif any(x in ticker for x in ['EPL', 'LALIGA', 'BUNDESLIGA', 'LIGUE1', 'SERIEA', 'MLS',
                                        'UCL', 'UEL', 'UECL', 'FACUP', 'COPADELREY', 'COPPAITALIA',
                                        'BRASILEIRO', 'LIGAMX', 'ARGPREMDIV', 'BELGIANPL', 'EREDIVISIE',
                                        'EKSTRAKLASA', 'LIGAPORTUGAL', 'SAUDIPL', 'SCOTTISHPREM',
                                        'SLGREECE', 'SUPERLIG', 'SWISSLEAGUE', 'ALEAGUE', 'JLEAGUE',
                                        'KLEAGUE', 'AFCCL', 'CLUBWC', 'AFCON', 'DFBPOKAL', 'EFLCHAMPIONSHIP',
                                        'EFLCUP', 'COUPEDEFRANCE', 'KNVBCUP', 'TACAPORT', 'HNL']):
            if 'EPL' in ticker:
                return ("Soccer", "English Premier League")
            elif 'LALIGA' in ticker:
                return ("Soccer", "La Liga")
            elif 'BUNDESLIGA' in ticker:
                return ("Soccer", "Bundesliga")
            elif 'LIGUE1' in ticker:
                return ("Soccer", "Ligue 1")
            elif 'SERIEA' in ticker:
                return ("Soccer", "Serie A")
            elif 'MLS' in ticker:
                return ("Soccer", "MLS")
            elif 'UCL' in ticker and 'UECL' not in ticker and 'UECL' not in ticker:
                return ("Soccer", "UEFA Champions League")
            elif 'UECL' in ticker:
                return ("Soccer", "UEFA Conference League")
            elif 'UEL' in ticker:
                return ("Soccer", "UEFA Europa League")
            elif 'FACUP' in ticker:
                return ("Soccer", "FA Cup")
            elif 'COPADELREY' in ticker:
                return ("Soccer", "Copa del Rey")
            elif 'COPPAITALIA' in ticker:
                return ("Soccer", "Coppa Italia")
            elif 'BRASILEIRO' in ticker:
                return ("Soccer", "Brasileiro Serie A")
            elif 'LIGAMX' in ticker:
                return ("Soccer", "Liga MX")
            elif 'ARGPREMDIV' in ticker:
                return ("Soccer", "Argentina Primera Division")
            elif 'BELGIANPL' in ticker:
                return ("Soccer", "Belgian Pro League")
            elif 'EREDIVISIE' in ticker:
                return ("Soccer", "Eredivisie")
            elif 'EKSTRAKLASA' in ticker:
                return ("Soccer", "Polish Ekstraklasa")
            elif 'LIGAPORTUGAL' in ticker:
                return ("Soccer", "Liga Portugal")
            elif 'SAUDIPL' in ticker:
                return ("Soccer", "Saudi Pro League")
            elif 'SCOTTISHPREM' in ticker:
                return ("Soccer", "Scottish Premiership")
            elif 'SLGREECE' in ticker:
                return ("Soccer", "Super League Greece")
            elif 'SUPERLIG' in ticker:
                return ("Soccer", "Turkish Super Lig")
            elif 'SWISSLEAGUE' in ticker:
                return ("Soccer", "Swiss Super League")
            elif 'ALEAGUE' in ticker:
                return ("Soccer", "Australian A-League")
            elif 'JLEAGUE' in ticker:
                return ("Soccer", "Japan J League")
            elif 'KLEAGUE' in ticker:
                return ("Soccer", "Korea K League")
            elif 'AFCCL' in ticker:
                return ("Soccer", "AFC Champions League")
            elif 'CLUBWC' in ticker:
                return ("Soccer", "Club World Cup")
            elif 'AFCON' in ticker:
                return ("Soccer", "AFCON")
            elif 'DFBPOKAL' in ticker:
                return ("Soccer", "DFB Pokal")
            elif 'EFLCHAMPIONSHIP' in ticker:
                return ("Soccer", "EFL Championship")
            elif 'EFLCUP' in ticker:
                return ("Soccer", "EFL Cup")
            elif 'COUPEDEFRANCE' in ticker:
                return ("Soccer", "Coupe de France")
            elif 'KNVBCUP' in ticker:
                return ("Soccer", "KNVB Cup")
            elif 'TACAPORT' in ticker:
                return ("Soccer", "Taca de Portugal")
            elif 'HNL' in ticker:
                return ("Soccer", "Croatia HNL")
            else:
                return ("Soccer", "Other")

        # HOCKEY (2nd level: NHL, International)
        elif any(x in ticker for x in ['NHL', 'HOCKEY', 'KHL', 'SHL', 'AHL', 'IIHF', 'WOHOCKEY', 'NCAAHOCKEY']):
            if 'NHL' in ticker:
                return ("Hockey", "NHL")
            elif 'KHL' in ticker:
                return ("Hockey", "KHL")
            elif 'SHL' in ticker:
                return ("Hockey", "SHL")
            elif 'AHL' in ticker:
                return ("Hockey", "AHL")
            elif 'IIHF' in ticker:
                return ("Hockey", "IIHF")
            elif 'WOHOCKEY' in ticker or 'WINTER OLYMPICS' in title:
                return ("Hockey", "Winter Olympics")
            elif 'NCAAHOCKEY' in ticker:
                return ("Hockey", "NCAA Hockey")
            else:
                return ("Hockey", "Other")

        # BASEBALL (2nd level: MLB, Other)
        elif 'MLB' in ticker or 'BASEBALL' in title:
            return ("Baseball", "MLB")

        # ESPORTS (2nd level: LOL, CS2/CSGO, Dota 2, Valorant, etc.)
        elif any(x in ticker for x in ['LOL', 'CS2', 'CSGO', 'DOTA2', 'VALORANT', 'COD', 'FIFA', 'R6', 'PPL']):
            if 'LOL' in ticker:
                return ("Esports", "League of Legends")
            elif 'CS2' in ticker or 'CSGO' in ticker:
                return ("Esports", "Counter-Strike")
            elif 'DOTA2' in ticker:
                return ("Esports", "Dota 2")
            elif 'VALORANT' in ticker:
                return ("Esports", "Valorant")
            elif 'COD' in ticker:
                return ("Esports", "Call of Duty")
            elif 'FIFA' in ticker:
                return ("Esports", "FIFA")
            elif 'R6' in ticker:
                return ("Esports", "Rainbow Six Siege")
            elif 'PPL' in ticker:
                return ("Esports", "Other")
            else:
                return ("Esports", "Other")

        # MMA/UFC
        elif 'UFC' in ticker:
            return ("MMA", "UFC")

        # BOXING
        elif 'BOXING' in ticker:
            return ("Boxing", "Boxing")

        # CRICKET
        elif 'CRICKET' in ticker or 'T20' in ticker:
            if 'T20' in ticker:
                return ("Cricket", "T20")
            elif 'ODI' in ticker:
                return ("Cricket", "ODI")
            else:
                return ("Cricket", "Other")

        # MOTORSPORT
        elif 'F1' in ticker:
            return ("Motorsport", "Formula 1")

        # GOLF
        elif 'PGA' in ticker:
            return ("Golf", "PGA")

        # DARTS
        elif 'DARTS' in ticker:
            return ("Darts", "Darts")

        # PICKLEBALL
        elif 'PICKLEBALL' in ticker:
            return ("Pickleball", "Pickleball")

        # LACROSSE
        elif 'LAX' in ticker or 'LACROSSE' in title:
            return ("Lacrosse", "NCAA Lacrosse")

        # WINTER OLYMPICS OTHER
        elif any(x in ticker for x in ['WOCURL', 'WOLUGE', 'WOSSKATE']):
            if 'WOCURL' in ticker:
                return ("Winter Olympics", "Curling")
            elif 'WOLUGE' in ticker:
                return ("Winter Olympics", "Luge")
            elif 'WOSSKATE' in ticker:
                return ("Winter Olympics", "Speed Skating")
            else:
                return ("Winter Olympics", "Other")

        # COLLEGE FOOTBALL PLAYOFF
        elif 'CFPSEED' in ticker:
            return ("Football", "NCAA Football Playoff")

        else:
            return ("Other Sports", None)

    # OTHER CATEGORIES (1-LAYER HIERARCHY)
    elif category == "Climate and Weather":
        if 'HIGH' in series_ticker or 'LOW' in series_ticker:
            return ("Temperature", None)
        elif 'RAIN' in series_ticker or 'SNOW' in series_ticker:
            return ("Precipitation", None)
        elif 'HURRICANE' in series_ticker or 'TORNADO' in series_ticker:
            return ("Severe Weather", None)
        else:
            return ("Other Weather", None)

    elif category == "Economics":
        if any(x in series_ticker for x in ['CPI', 'INFLATION', 'PCE']):
            return ("Inflation", None)
        elif any(x in series_ticker for x in ['FED', 'JOBLESS', 'PAYROLL', 'ADP', 'U3']):
            return ("Employment & Fed", None)
        elif any(x in series_ticker for x in ['GAS', 'OIL']):
            return ("Energy Prices", None)
        elif 'GDP' in series_ticker:
            return ("GDP", None)
        elif any(x in series_ticker for x in ['FRM', 'TNOTE']):
            return ("Interest Rates", None)
        else:
            return ("Other Economics", None)

    elif category == "Financials":
        if any(x in series_ticker for x in ['EUR', 'GBP', 'JPY']):
            return ("Forex", None)
        elif any(x in series_ticker for x in ['INXZ', 'NASDAQ']):
            return ("Stock Indices", None)
        elif 'GOLD' in series_ticker:
            return ("Commodities", None)
        elif 'TNOTE' in series_ticker:
            return ("Bonds", None)
        else:
            return ("Other Financials", None)

    elif category == "Crypto":
        if 'BTC' in series_ticker:
            return ("Bitcoin", None)
        elif 'ETH' in series_ticker:
            return ("Ethereum", None)
        elif 'SOL' in series_ticker:
            return ("Solana", None)
        elif 'XRP' in series_ticker:
            return ("XRP", None)
        else:
            return ("Other Crypto", None)

    elif category == "Health":
        if any(x in series_ticker for x in ['COVID', 'CASE', 'VAXX', 'BOOSTER']):
            return ("COVID-19", None)
        else:
            return ("Other Health", None)

    elif category == "Politics":
        if 'APPROVE' in series_ticker:
            return ("Approval Ratings", None)
        else:
            return ("Other Politics", None)

    elif category == "Mentions":
        return ("Mentions", None)

    elif category == "Companies":
        return ("Companies", None)

    elif category == "Science and Technology":
        if 'LLM' in series_ticker or 'MODEL' in series_ticker:
            return ("AI Models", None)
        elif 'TSA' in series_ticker:
            return ("Transportation", None)
        else:
            return ("Other Science & Tech", None)

    elif category == "Transportation":
        return ("Transportation", None)

    elif category == "World":
        if 'FLIGHT' in series_ticker:
            return ("Flight Delays", None)
        elif 'RAIN' in series_ticker:
            return ("Weather", None)
        else:
            return ("Other World", None)

    else:
        return ("Other", None)


def analyze_subcategories_with_hierarchy():
    """Analyze backtest data using Kalshi's actual hierarchical sub-category structure."""

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
    for path in df['Hierarchical_Path'].unique():
        path_df = df[df['Hierarchical_Path'] == path]
        total_markets = len(path_df)

        if total_markets >= 20:  # Minimum threshold
            correct = (path_df['Prediction Correct'] == 'CORRECT').sum()
            accuracy = correct / total_markets

            # Calculate expected value
            # Assuming average price across the range (85¢ to 98¢ → avg ~91.5¢)
            # EV = (accuracy × 100) - (price × 100) - (0.07 × price × (1-price) × 100)
            # Using 91.5¢ as representative price
            avg_price = 0.915
            profit_if_win = (1.00 - avg_price) * 100  # in cents
            loss_if_lose = avg_price * 100  # in cents
            fee = 0.07 * avg_price * (1 - avg_price) * 100  # in cents
            ev_per_contract = (accuracy * profit_if_win) - ((1 - accuracy) * loss_if_lose) - fee

            results.append({
                'Hierarchical_Path': path,
                'Total_Markets': total_markets,
                'Correct': correct,
                'Accuracy': accuracy,
                'EV_per_Contract': ev_per_contract,
                'Break_Even_Accuracy': (avg_price * 100 + fee) / 100
            })

    # Convert to DataFrame and sort
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Accuracy', ascending=False)

    # Filter for 90%+ accuracy
    high_accuracy = results_df[results_df['Accuracy'] >= 0.90].copy()

    print("=" * 100)
    print("HIERARCHICAL SUB-CATEGORIES WITH 90%+ ACCURACY AND 20+ MARKETS")
    print("=" * 100)
    print(f"\nFound {len(high_accuracy)} hierarchical sub-categories meeting criteria\n")

    # Print with proper formatting
    for idx, row in high_accuracy.iterrows():
        print(f"{row['Hierarchical_Path']}")
        print(f"  Markets: {row['Total_Markets']:,} | Accuracy: {row['Accuracy']:.1%} | EV: {row['EV_per_Contract']:.2f}¢")
        print()

    # Summary stats
    profitable = (high_accuracy['EV_per_Contract'] > 0).sum()
    print("=" * 100)
    print(f"Summary:")
    print(f"  Total sub-categories: {len(high_accuracy)}")
    print(f"  Profitable: {profitable} ({profitable/len(high_accuracy)*100:.1f}%)")
    print(f"  Total markets: {high_accuracy['Total_Markets'].sum():,}")
    print(f"  Average accuracy: {high_accuracy['Accuracy'].mean():.1%}")
    print(f"  Average EV: {high_accuracy['EV_per_Contract'].mean():.2f}¢")
    print("=" * 100)

    # Save summary to CSV
    output_file = 'hierarchical_subcategories_90plus.csv'
    high_accuracy.to_csv(output_file, index=False)
    print(f"\nSummary saved to {output_file}")

    # Save detailed market-by-market data
    detailed_file = 'hierarchical_markets_detailed.csv'

    # Filter to only markets in sub-categories with 90%+ accuracy and 20+ markets
    qualifying_paths = set(high_accuracy['Hierarchical_Path'].values)
    detailed_df = df[df['Hierarchical_Path'].isin(qualifying_paths)].copy()

    # Sort by hierarchical path, then by date
    detailed_df = detailed_df.sort_values(['Hierarchical_Path', 'First Touch Time'])

    # Select relevant columns for analysis
    columns_to_save = [
        'Hierarchical_Path', 'Category', 'Sub_Category', 'Sub_Sub_Category',
        'Series Ticker', 'Series Title', 'Ticker', 'Title',
        'Result', 'Settlement (¢)', 'First Touch Price (¢)',
        'First Touch Time', 'Permanent Cross Time', 'Market Close Time',
        'Prediction Correct', 'Trades Count'
    ]

    detailed_df[columns_to_save].to_csv(detailed_file, index=False)
    print(f"Detailed market data saved to {detailed_file} ({len(detailed_df):,} markets)")

    return high_accuracy, detailed_df


if __name__ == "__main__":
    analyze_subcategories_with_hierarchy()
