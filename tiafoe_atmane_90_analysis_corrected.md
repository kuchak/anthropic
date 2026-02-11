# Tiafoe vs Atmane 90% Crossing Analysis - CORRECTED
## Dallas Open - February 9, 2026

---

## Match Details

- **Event:** Dallas Open Round of 32
- **Players:** Frances Tiafoe vs Terence Atmane
- **Scheduled:** February 9, 2026, 11:00 AM ET
- **Match Start:** February 10, 2026, 01:05:00 UTC
- **Winner:** Frances Tiafoe (both platforms confirmed)

---

## KALSHI Analysis

**Market:** KXATPMATCH-26FEB09ATMTIA-TIA

### Market Info:
- **Question:** "Will Frances Tiafoe win the Atmane vs Tiafoe: Round Of 32 match?"
- **Status:** Finalized
- **Result:** ✅ **YES** (Tiafoe won)
- **Settlement Value:** 100¢
- **Volume:** $459,682
- **Market Open:** Feb 8, 2026 18:06 UTC
- **Market Close:** Feb 10, 2026 03:02 UTC

### ⏰ 90% CROSSING - EXACT TIMESTAMP:

**🎯 FIRST TOUCH OF 90%:**
- **Timestamp:** `2026-02-10T02:29:51.504149Z`
- **Price:** 91¢
- **Time:** 02:29:51 UTC (1 hour 25 minutes after match start)

**Context before first touch:**
```
2026-02-10T02:29:17Z  88¢
2026-02-10T02:29:17Z  87¢
2026-02-10T02:29:44Z  84¢
2026-02-10T02:29:51Z  91¢  <-- FIRST HIT 90%
2026-02-10T02:29:53Z  89¢  (bounced back down)
```

**🎯 PERMANENT CROSSING (Stayed Above 90%):**
- **Last trade below 90%:** `2026-02-10T02:45:08.927456Z` at 89¢
- **First trade above 90% (permanent):** `2026-02-10T02:45:10.038998Z` at 91¢
- **Time:** 02:45:10 UTC (1 hour 40 minutes after match start)

**Context of permanent crossing:**
```
2026-02-10T02:45:05Z  89¢
2026-02-10T02:45:05Z  91¢  (brief spike)
2026-02-10T02:45:08Z  89¢  <-- LAST TRADE BELOW 90%
2026-02-10T02:45:10Z  91¢  <-- PERMANENTLY CROSSED 90%
2026-02-10T02:45:10Z  91¢
2026-02-10T02:45:16Z  91¢
2026-02-10T02:45:19Z  91¢
... stayed above 90% from here onwards
```

### Price Movement Timeline:
- **Feb 8, 19:00:** 77¢
- **Feb 9, all day:** 75-78¢ (stable range)
- **Feb 10, 01:05:** Match starts
- **Feb 10, 02:00-02:29:** 50-88¢ (volatile during match)
- **Feb 10, 02:29:51:** **FIRST TOUCHED 91¢** ✅
- **Feb 10, 02:29-02:45:** Bounced between 89-93¢ (around 90% line)
- **Feb 10, 02:45:10:** **PERMANENTLY CROSSED TO 91¢** ✅
- **Feb 10, later:** Moved to 99¢+

---

## POLYMARKET Analysis

**Market:** atp-atmane-tiafoe-2026-02-09

### Market Info:
- **Question:** "Dallas Open: Terence Atmane vs Frances Tiafoe"
- **Condition ID:** 0xed15496bfdceaca7feec1c591c436c87d6b58be65239101d92b1eb382a9e26d8
- **Status:** Closed & Resolved
- **Result:** ✅ **TIAFOE WON** (settled at 100%)
- **Outcomes:** ["Atmane", "Tiafoe"]
- **Outcome Prices:** ["0", "1"] ← Tiafoe = 1 (100%)
- **Volume:** $323,852
- **Market Created:** Feb 7, 2026 23:00 UTC
- **Market Closed:** Feb 10, 2026 05:17 UTC

### ⏰ 90% Crossing on Polymarket:

⚠️ **Unable to retrieve historical price data** due to API limitations:
- CLOB API requires authentication for trades endpoint
- Price history endpoint has strict time window limits
- All attempted queries returned errors or empty results

**Status:** ❌ **DATA NOT AVAILABLE**

The Polymarket CLOB API does not provide public access to historical price data for this timeframe.

---

## SUMMARY

### Question: "When did Tiafoe odds cross 90% on each platform?"

#### KALSHI - EXACT TIMESTAMPS:

✅ **First touched 90%:** February 10, 2026, **02:29:51.504149 UTC**
- Price: 91¢
- ~1 hour 25 minutes after match start

✅ **Permanently crossed 90%:** February 10, 2026, **02:45:10.038998 UTC**
- Price: 91¢
- ~1 hour 40 minutes after match start
- Never went below 90% again after this

**Interpretation:**
- Tiafoe's odds first spiked above 90% at 02:29:51 UTC
- The market was volatile, bouncing between 89-93¢ for ~15 minutes
- At 02:45:10 UTC, the price permanently settled above 90%
- This occurred during the match as Tiafoe was securing the win

#### POLYMARKET:

❌ **Historical price data unavailable**
- Market confirmed to have settled with Tiafoe at 100%
- API does not provide public access to historical prices
- Cannot determine exact crossing timestamp

---

## Settlement Verification

✅ **Both platforms correctly settled:**
- **Kalshi:** Tiafoe won (100¢)
- **Polymarket:** Tiafoe won (100% = price 1.00)

**Frances Tiafoe** won the match against Terence Atmane.

---

## Data Sources

- **Kalshi API:** `https://api.elections.kalshi.com/trade-api/v2`
  - Trades endpoint: `/markets/trades?ticker=KXATPMATCH-26FEB09ATMTIA-TIA`
  - Retrieved 1,000 trades with exact timestamps

- **Polymarket Gamma API:** `https://gamma-api.polymarket.com`
  - Market metadata retrieved successfully
  - Historical prices not publicly available via CLOB API

**Analysis Date:** February 11, 2026
**Data Source:** Live trade data from Kalshi API
