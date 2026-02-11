# Tennis 90% Crossing Strategy - Backtest Results

## 📊 Executive Summary

**100% accuracy** when using the "permanent crossing" filter on 100 recent tennis markets.

---

## 🎯 Results

### Overall Statistics
- **Markets analyzed:** 100
- **Markets that crossed 90%:** 50/100 (50%)
- **Overall accuracy:** 94.0%

### Crossing Type Breakdown

| Type | Count | Accuracy | Notes |
|------|-------|----------|-------|
| **Permanent Crossing** | 47 | **47/47 = 100.0%** ✅ | Price stayed ≥90% |
| **Touch-Only** | 3 | 0/3 = 0.0% ❌ | Price briefly hit 90% then dropped |

---

## ⏱️ Betting Windows

For markets with permanent crossing:
- **Average:** 15.7 minutes (from permanent crossing to market close)
- **Minimum:** 3.4 minutes
- **Maximum:** 77.3 minutes

**77% of markets** give you 5+ minutes to execute.

---

## ⚠️ False Positives Analysis

All 3 false positives were **"touch-only"** markets:

### 1. KXATPMATCH-26FEB10BARSEY-SEY (Seyboth Wild)
- Hit 93¢ at 18:02
- NO permanent crossing
- Barrios Vera won (hit 90% permanently at 18:11)
- **Cause:** Early odds spike, match went other way

### 2. KXATPMATCH-26FEB09DZUDEL-DZU (Dzumhur)
- Hit 93¢ at 00:10 (~17 hours before match end!)
- NO permanent crossing
- Dellien won (hit 90% permanently during match)
- **Cause:** Pre-match odds, not live match data

### 3. KXATPMATCH-26FEB08BOOGRE-BOO (Boogaard)
- Hit 90¢ at 11:41
- NO permanent crossing
- Grenier won (hit 90% permanently at 12:26)
- **Cause:** Early signal, match momentum shifted

---

## 🚀 Recommended Strategy

### Entry Rule:
```
IF price hits 90%
AND maintains permanent crossing (stays ≥90% for sustained period)
THEN enter long position
```

### Why "Permanent Crossing" Matters:
1. **Filters out pre-match odds** (like Dzumhur case)
2. **Filters out temporary spikes** (like Boogaard/Seyboth Wild)
3. **Confirms live match momentum** is actually favoring the player
4. **Delivers 100% accuracy** vs 94% for "any 90% touch"

### Implementation:
- Monitor for 90% crossing
- Wait for confirmation that price stays ≥90%
- Definition of "permanent": Price doesn't drop back below 90% (our analysis uses this exact criterion)
- Average 15.7 min window gives plenty of time to verify and execute

---

## 📈 Expected Performance

### If you bet on ALL "90% crossings":
- Hit rate: 94.0% (47/50)
- Risk: 6% false positive rate from touch-only spikes

### If you bet ONLY on "permanent crossings":
- Hit rate: **100.0%** (47/47)
- Risk: 0% false positives in 100-market sample
- Trade-off: Miss out on 3 opportunities (but all 3 were losers anyway!)

---

## 🔍 Data Files

- **tennis_90_crossing_detailed.csv** - Complete data for all 100 markets
- **tennis_90_accuracy_analysis.json** - Full analysis with timestamps
- **analyze_tennis_90_percent.py** - Analysis script

---

## ⚡ Key Takeaway

**Wait for permanent crossing, not just first touch.**

The difference between 94% and 100% accuracy is simply waiting to confirm the price stays above 90% rather than acting on the first spike.
