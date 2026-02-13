# FINAL PROFITABLE WHITELIST - Data-Validated Configuration

## Executive Summary

**Critical Finding**: Only **30 out of 73** fast-stabilizing tickers are actually profitable at 90-92¢ entry.

### Validation Criteria
1. ✅ Fast/medium stabilization (< 60 min median gap)
2. ✅ Profitable accuracy (> 91% at 90-92¢ entry)

### Results
- **30 tickers** meet BOTH criteria (41.1% pass rate)
- **43 tickers** rejected for low accuracy (58.9% fail rate)
- **Overall accuracy**: 94.27% (1,629 wins / 1,728 markets)

---

## FAST MARKETS (1-minute wait) - 5 tickers

**Best for high-frequency trading** - Stabilize in 2.5-4.6 minutes

| Rank | Ticker | Category | Markets | Accuracy | Median Gap |
|------|--------|----------|---------|----------|------------|
| 1 | **KXBTC15M** | Bitcoin | 55 | **92.7%** | 3.4 min |
| 2 | **KXSOL15M** | Solana | 53 | **92.5%** | 3.4 min |
| 3 | **KXUCLGAME** | Soccer (UCL) | 51 | **92.2%** | 3.8 min |
| 4 | **KXEPLGAME** | Soccer (EPL) | 46 | **91.3%** | 2.5 min |
| 5 | **KXSUPERLIGGAME** | Soccer (Super Lig) | 56 | **91.1%** | 4.6 min |

**Total**: 261 markets, 91.9% average accuracy

**Key Findings**:
- ✅ Bitcoin/Solana 15-min markets are excellent (92%+ accuracy)
- ✅ Champions League better than domestic leagues
- ❌ KXETH15M rejected (90.0% accuracy - too low!)
- ❌ La Liga, Bundesliga, Eredivisie rejected (82-88% accuracy)

---

## MEDIUM MARKETS (3-minute wait) - 15 tickers

**High accuracy, good volume** - Stabilize in 5-15 minutes

| Rank | Ticker | Category | Markets | Accuracy | Median Gap |
|------|--------|----------|---------|----------|------------|
| 1 | **KXNCAAFGAME** | NCAA Football | 51 | **98.0%** 🏆 | 11.7 min |
| 2 | **KXWTAMATCH** | WTA Tennis | 88 | **96.6%** | 11.9 min |
| 3 | **KXSCOTTISHPREMGAME** | Scottish Prem | 52 | **96.2%** | 6.6 min |
| 4 | **KXNHLGAME** | NHL Hockey | 75 | **96.0%** | 7.6 min |
| 5 | **KXLIGUE1GAME** | Ligue 1 | 57 | **94.7%** | 6.0 min |
| 6 | **KXATPCHALLENGERMATCH** | ATP Challenger | 76 | **94.7%** | 12.5 min |
| 7 | **KXEUROLEAGUEGAME** | Euroleague Basketball | 89 | **94.4%** | 8.6 min |
| 8 | **KXNFLPREPACKSGP** | NFL Parlays | 32 | **93.8%** | 12.6 min |
| 9 | **KXNFLSPREAD** | NFL Spread | 46 | **93.5%** | 7.7 min |
| 10 | **KXUFCFIGHT** | MMA/UFC | 44 | **93.2%** | 5.3 min |
| 11 | **KXSAUDIPLGAME** | Saudi Pro League | 58 | **93.1%** | 8.3 min |
| 12 | **KXFACUPGAME** | FA Cup | 29 | **93.1%** | 9.8 min |
| 13 | **KXHNLGAME** | Eredivisie | 27 | **92.6%** | 7.6 min |
| 14 | **KXUNITEDCUPMATCH** | United Cup Tennis | 39 | **92.3%** | 12.0 min |
| 15 | **KXUELGAME** | Europa League | 58 | **91.4%** | 5.6 min |

**Total**: 821 markets, 94.2% average accuracy

**Key Findings**:
- 🏆 NCAA Football is the HIGHEST accuracy (98.0%!)
- ✅ Tennis markets (WTA, ATP Challenger, United Cup) are excellent
- ✅ NHL Hockey very reliable (96.0%, large sample size)
- ✅ Scottish Prem outperforms bigger leagues (96.2%)
- ❌ Serie A, MLS, many other soccer leagues rejected (80-87% accuracy)

---

## SLOW MARKETS (5-minute wait) - 10 tickers

**Highest accuracy tier** - Stabilize in 16-58 minutes

| Rank | Ticker | Category | Markets | Accuracy | Median Gap |
|------|--------|----------|---------|----------|------------|
| 1 | **KXATPMATCH** | ATP Tennis | 70 | **97.1%** 🏆 | 18.3 min |
| 2 | **KXHIGHLAX** | LA Temperature | 28 | **96.4%** | 52.7 min |
| 3 | **KXNCAAFTOTAL** | NCAA Football Total | 105 | **96.2%** | 45.1 min |
| 4 | **KXNBATOTAL** | NBA Total Points | 84 | **95.2%** | 25.5 min |
| 5 | **KXNFLTOTAL** | NFL Total Points | 78 | **94.9%** | 26.5 min |
| 6 | **KXFIFAGAME** | FIFA Esports | 58 | **94.8%** | 16.8 min |
| 7 | **KXMLBGAME** | MLB Game Winner | 65 | **93.8%** | 29.6 min |
| 8 | **KXINXZ** | Stock Indices | 46 | **93.5%** | 50.0 min |
| 9 | **KXWTACHALLENGERMATCH** | WTA Challenger | 72 | **93.1%** | 28.6 min |
| 10 | **KXMLBSPREAD** | MLB Spread | 40 | **92.5%** | 30.3 min |

**Total**: 646 markets, 94.8% average accuracy

**Key Findings**:
- 🏆 ATP Tennis (main tour) is 97.1% accurate!
- ✅ NCAA Football TOTAL is excellent (96.2%, largest sample: 105 markets)
- ✅ NBA/NFL totals are reliable (95%+)
- ✅ Temperature markets work (LA: 96.4%)
- ✅ MLB is profitable (93-94%)
- ❌ CS2, CS:GO, Valorant, CoD esports all rejected (77-91% accuracy)
- ❌ WNBA rejected (86.5% accuracy)

---

## REJECTED TICKERS - 43 tickers failed profitability test

### Major Surprises (Fast but NOT Profitable)

| Ticker | Category | Wait | Markets | Accuracy | Why Rejected |
|--------|----------|------|---------|----------|--------------|
| KXETH15M | Ethereum | 1m | 60 | 90.0% | Just below threshold |
| KXLALIGAGAME | La Liga | 1m | 57 | 87.7% | Too volatile |
| KXBUNDESLIGAGAME | Bundesliga | 1m | 58 | 86.2% | Too volatile |
| KXEREDIVISIEGAME | Eredivisie | 1m | 67 | 82.1% | Very volatile |
| KXLOLGAME | League of Legends | 3m | 100 | 89.0% | Esports volatility |
| KXDOTA2GAME | Dota 2 | 3m | 58 | 87.9% | Esports volatility |
| KXMLSGAME | MLS | 3m | 63 | 87.3% | Too volatile |
| KXSERIEAGAME | Serie A | 3m | 61 | 86.9% | Too volatile |
| KXCS2GAME | CS2 | 5m | 65 | 90.8% | Just below threshold |
| KXWNBAGAME | WNBA | 5m | 89 | 86.5% | Too volatile |
| KXNCAABMENTION | NCAA Basketball Mentions | 5m | 86 | 66.3% | Very poor! |

**Pattern**: Most soccer leagues (except UCL, EPL, Scottish Prem, Ligue 1) are too volatile.

---

## RECOMMENDED BOT CONFIGURATION

### config.yaml

```yaml
# === PROFITABLE TICKERS ONLY (30 tickers, 94.27% accuracy) ===
series_ticker_whitelist:
  # FAST (1-minute wait) - 5 tickers
  - KXBTC15M              # Bitcoin 15m (92.7%, n=55)
  - KXSOL15M              # Solana 15m (92.5%, n=53)
  - KXUCLGAME             # Champions League (92.2%, n=51)
  - KXEPLGAME             # EPL (91.3%, n=46)
  - KXSUPERLIGGAME        # Super Lig (91.1%, n=56)

  # MEDIUM (3-minute wait) - 15 tickers
  - KXNCAAFGAME           # NCAA Football (98.0%, n=51) 🏆 BEST
  - KXWTAMATCH            # WTA Tennis (96.6%, n=88)
  - KXSCOTTISHPREMGAME    # Scottish Prem (96.2%, n=52)
  - KXNHLGAME             # NHL Hockey (96.0%, n=75)
  - KXLIGUE1GAME          # Ligue 1 (94.7%, n=57)
  - KXATPCHALLENGERMATCH  # ATP Challenger (94.7%, n=76)
  - KXEUROLEAGUEGAME      # Euroleague Basketball (94.4%, n=89)
  - KXNFLPREPACKSGP       # NFL Parlays (93.8%, n=32)
  - KXNFLSPREAD           # NFL Spread (93.5%, n=46)
  - KXUFCFIGHT            # MMA/UFC (93.2%, n=44)
  - KXSAUDIPLGAME         # Saudi Pro League (93.1%, n=58)
  - KXFACUPGAME           # FA Cup (93.1%, n=29)
  - KXHNLGAME             # Eredivisie (92.6%, n=27)
  - KXUNITEDCUPMATCH      # United Cup Tennis (92.3%, n=39)
  - KXUELGAME             # Europa League (91.4%, n=58)

  # SLOW (5-minute wait) - 10 tickers
  - KXATPMATCH            # ATP Tennis (97.1%, n=70)
  - KXHIGHLAX             # LA Temperature (96.4%, n=28)
  - KXNCAAFTOTAL          # NCAA Football Total (96.2%, n=105)
  - KXNBATOTAL            # NBA Total (95.2%, n=84)
  - KXNFLTOTAL            # NFL Total (94.9%, n=78)
  - KXFIFAGAME            # FIFA Esports (94.8%, n=58)
  - KXMLBGAME             # MLB Game (93.8%, n=65)
  - KXINXZ                # Stock Indices (93.5%, n=46)
  - KXWTACHALLENGERMATCH  # WTA Challenger (93.1%, n=72)
  - KXMLBSPREAD           # MLB Spread (92.5%, n=40)

# === WAIT TIMES ===
series_ticker_wait_times:
  # Fast (1 minute)
  KXBTC15M: 1
  KXSOL15M: 1
  KXUCLGAME: 1
  KXEPLGAME: 1
  KXSUPERLIGGAME: 1

  # Medium (3 minutes)
  KXNCAAFGAME: 3
  KXWTAMATCH: 3
  KXSCOTTISHPREMGAME: 3
  KXNHLGAME: 3
  KXLIGUE1GAME: 3
  KXATPCHALLENGERMATCH: 3
  KXEUROLEAGUEGAME: 3
  KXNFLPREPACKSGP: 3
  KXNFLSPREAD: 3
  KXUFCFIGHT: 3
  KXSAUDIPLGAME: 3
  KXFACUPGAME: 3
  KXHNLGAME: 3
  KXUNITEDCUPMATCH: 3
  KXUELGAME: 3

  # Slow (5 minutes)
  KXATPMATCH: 5
  KXHIGHLAX: 5
  KXNCAAFTOTAL: 5
  KXNBATOTAL: 5
  KXNFLTOTAL: 5
  KXFIFAGAME: 5
  KXMLBGAME: 5
  KXINXZ: 5
  KXWTACHALLENGERMATCH: 5
  KXMLBSPREAD: 5
```

---

## Expected Performance

### Overall (All 30 Profitable Tickers)
- **Total Markets**: 1,728
- **Wins**: 1,629
- **Losses**: 99
- **Accuracy**: **94.27%**
- **Estimated ROI**: ~3-5% per bet (after fees)

### By Wait Time Category

| Category | Tickers | Markets | Accuracy | Coverage |
|----------|---------|---------|----------|----------|
| **Fast (1m)** | 5 | 261 | 91.9% | 15.1% |
| **Medium (3m)** | 15 | 821 | 94.2% | 47.5% |
| **Slow (5m)** | 10 | 646 | 94.8% | 37.4% |

---

## Key Insights

### ✅ What Works

1. **NCAA Football** is the BEST market (98.0% accuracy)
2. **Tennis** (ATP/WTA) is consistently excellent (93-97%)
3. **NHL Hockey** is very reliable (96.0%)
4. **Crypto 15-minute markets** (BTC/SOL) work well
5. **Champions League** > domestic soccer leagues
6. **NFL/NBA totals** > spreads/player props
7. **Scottish Prem** outperforms bigger leagues

### ❌ What Doesn't Work

1. **Most soccer leagues** (La Liga, Bundesliga, Serie A, MLS, etc.) - 80-87% accuracy
2. **Ethereum 15m** - Just missed (90.0%)
3. **Most esports** (LoL, Dota2, CS:GO, Valorant, CoD) - Too volatile
4. **WNBA** - 86.5% accuracy (vs NBA 95.2%)
5. **Mention markets** - Very poor (66-89%)

### 🎯 Strategic Recommendations

**Tier 1 (Highest Priority)**: Focus here first
- NCAA Football (98.0%)
- ATP/WTA Tennis (93-97%)
- NHL Hockey (96.0%)
- Champions League (92.2%)

**Tier 2 (High Volume)**: Good accuracy + many opportunities
- NFL Spread/Total (93-95%)
- NBA Total (95.2%)
- Crypto 15m (BTC/SOL) (92-93%)
- Euroleague Basketball (94.4%)

**Tier 3 (Supplemental)**: Good accuracy, lower volume
- MLB (93-94%)
- Scottish Prem (96.2%)
- FIFA Esports (94.8%)
- Temperature (LA) (96.4%)

---

## Implementation Checklist

- [ ] Update `config.yaml` with 30-ticker whitelist
- [ ] Add ticker-specific wait times (1m, 3m, or 5m)
- [ ] Implement stability tracking (time since first 90¢ touch)
- [ ] Test with paper trading first
- [ ] Monitor win rate by ticker
- [ ] Adjust whitelist based on live performance

---

## Data Sources

- **Backtest Period**: Historical Kalshi markets (comprehensive dataset)
- **Markets Analyzed**: 15,777 total, 9,022 in 90-92¢ range
- **Validation Date**: 2026-02-13
- **Profitability Threshold**: 91% accuracy minimum
- **Files**:
  - `comprehensive_crossed_90_detailed.csv` (accuracy data)
  - `stability_waiting_period_by_ticker.csv` (wait time data)
  - `profitable_tickers_with_wait_times.csv` (validated results)
  - `profitable_ticker_wait_times.yaml` (bot config)

---

## Bottom Line

**30 tickers, 94.27% accuracy, 1,728 markets validated.**

This is the definitive, data-validated whitelist for profitable 90¢ betting.
