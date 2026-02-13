# Series Ticker Wait Times - Complete Configuration

## Overview

Based on backtest analysis of 5,255 markets that dropped back below 90¢, we've calculated optimal wait times for each series ticker. This prevents premature betting on temporary price spikes.

**Key Insight**: Different market types stabilize at different speeds.
- Soccer/Crypto: 2-5 minutes (bet after 1 min wait)
- Tennis/Esports/Hockey: 5-15 minutes (bet after 3 min wait)
- MLB/NBA/Slower markets: 15-60 minutes (bet after 5 min wait)
- Mentions/Weather/Long-term: 60+ minutes to DAYS (EXCLUDE)

---

## Summary Statistics

| Category | Count | % of Total |
|----------|-------|------------|
| **FAST (1-min wait)** | 9 | 8.8% |
| **MEDIUM (3-min wait)** | 32 | 31.4% |
| **SLOW (5-min wait)** | 32 | 31.4% |
| **EXCLUDED (60+ min)** | 29 | 28.4% |
| **TOTAL ANALYZED** | 102 | 100% |

**Tradeable Markets**: 73 series tickers (71.6%)
**Excluded Markets**: 29 series tickers (28.4%)

---

## FAST STABILIZATION (1-minute wait)

**Median Gap: < 5 minutes**

These markets stabilize VERY quickly. Once price hits 90¢, wait just 1 minute before betting.

| Series Ticker | Category | Median Gap | Sample Size | Accuracy |
|---------------|----------|------------|-------------|----------|
| KXEPLGAME | Soccer (EPL) | 2.5 min | 31 | High |
| KXBTC15M | Bitcoin | 3.4 min | 26 | High |
| KXSOL15M | Solana | 3.4 min | 28 | High |
| KXBUNDESLIGAGAME | Soccer (Bundesliga) | 3.7 min | 36 | High |
| KXLALIGAGAME | Soccer (La Liga) | 3.7 min | 41 | High |
| KXUCLGAME | Soccer (Champions League) | 3.8 min | 31 | High |
| KXETH15M | Ethereum | 4.1 min | 34 | High |
| KXEREDIVISIEGAME | Soccer (Eredivisie) | 4.3 min | 36 | High |
| KXSUPERLIGGAME | Soccer (Super Lig) | 4.6 min | 34 | High |

**Pattern**: Fast in-game markets with live odds updates. Soccer and crypto 15-minute markets dominate.

---

## MEDIUM STABILIZATION (3-minute wait)

**Median Gap: 5-15 minutes**

| Series Ticker | Category | Median Gap | Sample Size |
|---------------|----------|------------|-------------|
| KXSERIEAGAME | Soccer (Serie A) | 5.2 min | 34 |
| KXUFCFIGHT | MMA | 5.3 min | 26 |
| KXUELGAME | Soccer (Europa League) | 5.6 min | 45 |
| KXLIGUE1GAME | Soccer (Ligue 1) | 6.0 min | 44 |
| KXEFLCHAMPIONSHIPGAME | Soccer (Championship) | 6.3 min | 34 |
| KXAFCONGAME | Soccer (AFC) | 6.3 min | 35 |
| KXALEAGUEGAME | Soccer (A-League) | 6.4 min | 42 |
| KXUECLGAME | Soccer (Europa Conference) | 6.5 min | 30 |
| KXSWISSLEAGUEGAME | Soccer (Swiss) | 6.6 min | 27 |
| KXSCOTTISHPREMGAME | Soccer (Scottish Prem) | 6.6 min | 33 |
| KXARGPREMDIVGAME | Soccer (Argentina) | 7.0 min | 44 |
| KXLIGAPORTUGALGAME | Soccer (Portugal) | 7.0 min | 36 |
| KXMLSGAME | Soccer (MLS) | 7.1 min | 42 |
| KXFIBACHAMPLEAGUEGAME | Basketball (FIBA) | 7.1 min | 31 |
| KXBELGIANPLGAME | Soccer (Belgium) | 7.5 min | 37 |
| KXNHLGAME | Hockey (NHL) | 7.6 min | 53 |
| KXHNLGAME | Soccer (Eredivisie) | 7.6 min | 20 |
| KXNFLSPREAD | Football (NFL Spread) | 7.7 min | 38 |
| KXBRASILEIROGAME | Soccer (Brazil) | 7.8 min | 48 |
| KXLIGAMXGAME | Soccer (Liga MX) | 8.0 min | 40 |
| KXSAUDIPLGAME | Soccer (Saudi) | 8.3 min | 48 |
| KXEUROLEAGUEGAME | Basketball (Euroleague) | 8.6 min | 75 |
| KXLOLMAP | Esports (LoL Maps) | 9.4 min | 24 |
| KXFACUPGAME | Soccer (FA Cup) | 9.8 min | 22 |
| KXNCAAFGAME | Football (NCAA) | 11.7 min | 30 |
| KXWTAMATCH | Tennis (WTA) | 11.9 min | 69 |
| KXUNITEDCUPMATCH | Tennis (United Cup) | 12.0 min | 31 |
| KXNBLGAME | Basketball (NBL) | 12.2 min | 47 |
| KXATPCHALLENGERMATCH | Tennis (ATP Challenger) | 12.5 min | 56 |
| KXNFLPREPACKSGP | Football (NFL Parlays) | 12.6 min | 23 |
| KXLOLGAME | Esports (LoL Games) | 12.8 min | 60 |
| KXDOTA2GAME | Esports (Dota 2) | 14.4 min | 29 |

**Pattern**: Mid-tier soccer leagues, tennis, hockey, esports. More variability than fast markets.

---

## SLOW STABILIZATION (5-minute wait)

**Median Gap: 15-60 minutes**

| Series Ticker | Category | Median Gap | Sample Size |
|---------------|----------|------------|-------------|
| KXFIFAGAME | Esports (FIFA) | 16.8 min | 42 |
| KXATPMATCH | Tennis (ATP) | 18.3 min | 51 |
| KXEUROCUPGAME | Golf (Euro Cup) | 18.7 min | 62 |
| KXCBAGAME | Basketball (CBA) | 18.8 min | 80 |
| KXCS2GAME | Esports (CS2) | 20.9 min | 51 |
| KXLALIGATOTAL | Soccer (La Liga Total) | 22.9 min | 23 |
| KXCLUBWCGAME | Soccer (Club World Cup) | 24.7 min | 34 |
| KXCSGOGAME | Esports (CS:GO) | 25.3 min | 59 |
| KXNBATOTAL | Basketball (NBA Total) | 25.5 min | 62 |
| KXNFLTOTAL | Football (NFL Total) | 26.5 min | 50 |
| KXKBLGAME | Basketball (KBL) | 26.8 min | 37 |
| KXWTACHALLENGERMATCH | Tennis (WTA Challenger) | 28.6 min | 51 |
| KXMLBGAME | Baseball (MLB) | 29.6 min | 42 |
| KXMLBSPREAD | Baseball (MLB Spread) | 30.3 min | 29 |
| KXVALORANTGAME | Esports (Valorant) | 30.3 min | 42 |
| KXWNBAGAME | Basketball (WNBA) | 31.1 min | 62 |
| KXCODGAME | Esports (Call of Duty) | 32.4 min | 23 |
| KXUCLTOTAL | Soccer (UCL Total) | 35.0 min | 33 |
| KXJBLEAGUEGAME | Basketball (J.League) | 39.0 min | 45 |
| KXEPLTOTAL | Soccer (EPL Total) | 40.0 min | 39 |
| KXMAMDANIMENTION | Mentions (Mamadani) | 41.7 min | 27 |
| KXNCAAFSPREAD | Football (NCAA Spread) | 42.5 min | 48 |
| KXNCAAFTOTAL | Football (NCAA Total) | 45.1 min | 75 |
| KXKHLGAME | Hockey (KHL) | 46.0 min | 20 |
| KXNCAABMENTION | Mentions (NCAA Basketball) | 46.9 min | 35 |
| KXBUNDESLIGATOTAL | Soccer (Bundesliga Total) | 47.3 min | 29 |
| KXINXZ | Stock Indices | 50.0 min | 21 |
| KXHIGHAUS | Temperature (Austin) | 50.2 min | 26 |
| KXHIGHLAX | Temperature (LA) | 52.7 min | 26 |
| KXHIGHDEN | Temperature (Denver) | 53.6 min | 23 |
| KXLNBELITEGAME | Basketball (LNB Elite) | 54.3 min | 24 |
| KXNHLTOTAL | Hockey (NHL Total) | 58.8 min | 57 |

**Pattern**: Totals/spreads (not winner), player props, temperature, some esports. Slower to stabilize.

---

## EXCLUDED TICKERS (60+ minutes median gap)

**DO NOT TRADE** - Too unstable for real-time betting

| Series Ticker | Category | Median Gap | Sample Size | Reason |
|---------------|----------|------------|-------------|--------|
| KXCRICKETT20IMATCH | Cricket | 1.1 hours | 20 | Slow stabilization |
| KXHOCHULMENTION | Mentions | 1.1 hours | 44 | Mention markets volatile |
| KXFOMEN | Tennis | 1.2 hours | 26 | Long matches |
| KXNFLPASSYDS | Football | 1.5 hours | 61 | Player props unstable |
| KXNFLRSHYDS | Football | 1.5 hours | 50 | Player props unstable |
| KXFOWOMEN | Tennis | 1.6 hours | 27 | Long matches |
| KXNFLRECYDS | Football | 1.6 hours | 28 | Player props unstable |
| KXHIGHMIA | Temperature | 1.7 hours | 24 | Weather updates slow |
| KXHIGHCHI | Temperature | 1.9 hours | 21 | Weather updates slow |
| KXNFLTEAMTOTAL | Football | 2.0 hours | 57 | Game totals volatile |
| KXHIGHNY | Temperature | 2.1 hours | 22 | Weather updates slow |
| KXHIGHHOU | Temperature | 2.2 hours | 20 | Weather updates slow |
| KXCONGRESSMENTION | Mentions | 2.2 hours | 76 | News-driven volatility |
| KXNFLREC | Football | 2.6 hours | 41 | Player props unstable |
| KXNFLMENTION | Mentions | 3.0 hours | 41 | Mention markets volatile |
| KXSNLMENTION | Mentions | 3.1 hours | 20 | TV mentions volatile |
| KXTRUMPMENTIONB | Mentions | 3.8 hours | 61 | Political mentions volatile |
| KXCASED | COVID-19 | 4.2 hours | 27 | Daily data updates |
| KXVANCEMENTION | Mentions | 8.1 hours | 32 | News-driven |
| KXNCAAMENTION | Mentions | 10.3 hours | 37 | NCAA mentions volatile |
| KXRAINNYC | Precipitation | 11.0 hours | 22 | Weather forecasts change |
| KXTRUMPMENTION | Mentions | 11.1 hours | 29 | Political mentions volatile |
| KXNBAMENTION | Mentions | 15.2 hours | 42 | TV mentions volatile |
| KXKIMMELMENTION | Mentions | 21.6 hours | 31 | TV mentions volatile |
| KXCOLBERTMENTION | Mentions | 2.0 DAYS | 21 | TV mentions VERY volatile |
| KXSURVIVORMENTION | Mentions | 2.3 DAYS | 25 | TV mentions VERY volatile |
| KXAAAGASM | Energy Prices | 3.6 DAYS | 23 | Energy markets swing |
| KXMRBEASTMENTION | Mentions | 7.3 DAYS | 52 | Social media VERY volatile |
| KXGDP | GDP | 24.1 DAYS | 26 | Economic data swings |

**Pattern**: Mentions markets, weather, NFL player props, long-term economic data. Extremely volatile.

---

## Bot Implementation

### Recommended Wait Logic

```python
TICKER_WAIT_TIMES = {
    # Fast (1 minute)
    'KXEPLGAME': 1,
    'KXBTC15M': 1,
    'KXSOL15M': 1,
    'KXBUNDESLIGAGAME': 1,
    'KXLALIGAGAME': 1,
    'KXUCLGAME': 1,
    'KXETH15M': 1,
    'KXEREDIVISIEGAME': 1,
    'KXSUPERLIGGAME': 1,

    # Medium (3 minutes) - see full list in config
    # ...

    # Slow (5 minutes) - see full list in config
    # ...
}

def should_bet_on_market(ticker, current_price, time_since_first_90):
    """
    Check if enough time has passed for price stability.

    Args:
        ticker: Series ticker (e.g., 'KXEPLGAME')
        current_price: Current market price (0.90-0.92)
        time_since_first_90: Minutes since price first hit 90¢

    Returns:
        True if ready to bet, False if need to wait longer
    """
    # Check if ticker is in our configuration
    if ticker not in TICKER_WAIT_TIMES:
        return False  # Ticker not whitelisted (excluded)

    # Get required wait time for this ticker
    required_wait = TICKER_WAIT_TIMES[ticker]

    # Check if we've waited long enough
    if time_since_first_90 >= required_wait:
        # Price still at 90¢ after waiting → stable!
        if 0.90 <= current_price < 0.93:
            return True

    return False  # Not ready yet
```

### Recommended Whitelist

For fastest, most reliable markets:

```yaml
series_ticker_whitelist:
  # Fast soccer (1-min wait)
  - KXEPLGAME              # EPL (2.5 min gap)
  - KXBUNDESLIGAGAME       # Bundesliga (3.7 min gap)
  - KXLALIGAGAME           # La Liga (3.7 min gap)
  - KXUCLGAME              # Champions League (3.8 min gap)
  - KXEREDIVISIEGAME       # Eredivisie (4.3 min gap)
  - KXSUPERLIGGAME         # Super Lig (4.6 min gap)

  # Fast crypto (1-min wait)
  - KXBTC15M               # Bitcoin 15-min (3.4 min gap)
  - KXETH15M               # Ethereum 15-min (4.1 min gap)
  - KXSOL15M               # Solana 15-min (3.4 min gap)
```

---

## Expected Performance

### With Wait Times (Recommended)

| Wait Time | Markets Captured | Accuracy | Profitable? |
|-----------|------------------|----------|-------------|
| 1 min | 2,169 (24.0%) | 98.6% | ✅ YES |
| 5 min | 3,185 (35.3%) | 99.0% | ✅ YES |
| 30 min | 4,728 (52.4%) | 99.3% | ✅ YES |
| 60 min | 5,399 (59.8%) | 99.4% | ✅ YES |

### Without Wait Times (Current Bot)

| Bet Timing | Markets Captured | Accuracy | Profitable? |
|------------|------------------|----------|-------------|
| Immediate | 9,022 (100%) | ~76% | ❌ NO |

**Improvement**: +22.6% accuracy by waiting for stability!

---

## Data Source

- **Analysis Date**: 2026-02-13
- **Markets Analyzed**: 15,777 total, 9,022 in 90-92¢ range
- **Unstable Markets**: 5,255 (58.2% dropped back)
- **Data File**: `stability_waiting_period_by_ticker.csv`
- **Backtest Range**: Historical Kalshi markets that crossed 90%+ probability

---

## Key Takeaways

1. **58% of markets drop back** below 90¢ before stabilizing
2. **Soccer and crypto stabilize fastest** (2-5 minutes)
3. **Mentions and weather are EXTREMELY volatile** (hours to days)
4. **Waiting improves accuracy from ~76% to 99%+**
5. **Ticker-specific wait times are CRITICAL** for profitability
