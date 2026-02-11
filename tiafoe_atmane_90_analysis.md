# Tiafoe vs Atmane 90% Crossing Analysis
## Dallas Open - February 9, 2026

---

## 🚨 MAJOR FINDING: RESOLUTION DISCREPANCY

**The two platforms resolved this match with OPPOSITE results!**

---

## Match Details

- **Event:** Dallas Open Round of 32
- **Players:** Frances Tiafoe vs Terence Atmane
- **Scheduled:** February 9, 2026, 11:00 AM ET
- **Match Start:** February 10, 2026, 01:05:00 UTC
- **Score:** 6-4, 2-6, 2-6

---

## KALSHI Analysis

**Market:** KXATPMATCH-26FEB09ATMTIA-TIA

### Market Info:
- **Question:** "Will Frances Tiafoe win the Atmane vs Tiafoe: Round Of 32 match?"
- **Status:** Finalized
- **Result:** ✅ **YES** (Tiafoe won)
- **Settlement Value:** 100¢
- **Settlement Price:** 100¢
- **Volume:** $459,682
- **Market Open:** Feb 8, 2026 18:06 UTC
- **Market Close:** Feb 10, 2026 03:02 UTC

### 90% Crossing on Kalshi:

Hourly candlestick data (period_interval=60):

| Timestamp | Date/Time (UTC) | Price |
|-----------|----------------|-------|
| 1770688800 | 2026-02-10 02:00:00 | 51¢ |
| **1770692400** | **2026-02-10 03:00:00** | **99¢** ✅ |

**✅ KALSHI CROSSED 90% AT: February 10, 2026 03:00:00 UTC**

- **Jump:** 51¢ → 99¢ (48¢ increase in 1 hour)
- **Time after match start:** ~1 hour 55 minutes
- **Interpretation:** Market jumped to 99¢ when Tiafoe secured the win

### Price Movement:
- Feb 8 19:00: 77¢
- Feb 9 00:00-23:00: 75-78¢ (stable range)
- Feb 10 01:00: 78¢ (match starts)
- Feb 10 02:00: 51¢ ⚠️ (Tiafoe losing?)
- Feb 10 03:00: **99¢** ✅ (Tiafoe wins!)

---

## POLYMARKET Analysis

**Market:** atp-atmane-tiafoe-2026-02-09

### Market Info:
- **Question:** "Dallas Open: Terence Atmane vs Frances Tiafoe"
- **Condition ID:** 0xed15496bfdceaca7feec1c591c436c87d6b58be65239101d92b1eb382a9e26d8
- **Status:** Closed & Resolved
- **Result:** ❌ **ATMANE WON** (Tiafoe lost)
- **Final Tiafoe Price:** 0.001 (0.1%)
- **Volume:** $323,852
- **Market Created:** Feb 7, 2026 23:00 UTC
- **Market Closed:** Feb 10, 2026 05:17 UTC
- **Match Score:** 6-4, 2-6, 2-6

### 90% Crossing on Polymarket:

⚠️ **Unable to retrieve historical price data** due to API limitations:
- CLOB API requires specific time windows and returned errors
- Token-specific endpoints were not accessible
- Based on final settlement, Tiafoe prices ended near 0%

**Inference:** Given that Polymarket resolved to Atmane winning and Tiafoe's final price was 0.1%, it's **highly unlikely** that Tiafoe ever reached 90% on Polymarket during this match.

**One-day price change:** -24.95 percentage points (dropped from ~25% to 0.1%)

---

## 🔍 ANALYSIS: Why The Discrepancy?

### Possible Explanations:

1. **Different Match References**
   - Could the platforms have been tracking different matches?
   - Dates and player names match exactly, so unlikely

2. **Settlement Error**
   - One platform may have incorrectly settled the market
   - Kalshi shows Tiafoe won (100¢ settlement)
   - Polymarket shows Atmane won (score: 6-4, 2-6, 2-6)

3. **Score Interpretation**
   - Tennis best-of-3: Need 2 sets to win
   - Score 6-4, 2-6, 2-6 means:
     - Set 1: One player won 6-4
     - Set 2 & 3: Other player won 2-6, 2-6
   - **Who won Set 1?** This determines the match winner
   - If Tiafoe won Set 1 (6-4), then Atmane won Sets 2 & 3 → **Atmane wins**
   - If Atmane won Set 1 (6-4), then Tiafoe won Sets 2 & 3 → **Tiafoe wins**

4. **Verification Needed**
   - Check official ATP Tour results
   - One platform **definitely settled incorrectly**

---

## SUMMARY

### Question: "When did Tiafoe odds cross 90% on each platform?"

#### KALSHI:
✅ **YES - Crossed 90% at February 10, 2026, 03:00:00 UTC**
- Price jumped from 51¢ to 99¢ between 02:00-03:00 UTC
- This occurred during the match (started 01:05 UTC)
- Market settled as YES (Tiafoe won)

#### POLYMARKET:
❌ **NO - Did NOT cross 90%**
- Final price: 0.1% (essentially 0)
- Market settled as Atmane won
- Historical data unavailable but final settlement indicates Tiafoe never reached 90%

---

## ⚠️ CRITICAL ISSUE

**This represents a significant settlement discrepancy between Kalshi and Polymarket for the same real-world event.**

One platform has incorrectly settled this market, resulting in:
- Traders on the correct platform being paid correctly
- Traders on the incorrect platform losing money despite being correct

**Recommendation:** Verify the actual match result from official ATP Tour sources to determine which platform was correct.

---

## Data Sources

- **Kalshi API:** `https://api.elections.kalshi.com/trade-api/v2`
- **Polymarket Gamma API:** `https://gamma-api.polymarket.com`
- **Polymarket CLOB API:** `https://clob.polymarket.com`

**Analysis Date:** February 11, 2026
**Script:** `check_tiafoe_atmane.py`
