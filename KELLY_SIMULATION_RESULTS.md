# Kelly Criterion Simulation Results

## 📊 **Simulation Overview**

Tested different Kelly fractions and bet caps against **10,472 real backtest markets** (50-98¢ range, 98.8% win rate).

**Parameters:**
- Starting Bankroll: $1,000
- Markets: 10,472 (sorted by timestamp)
- Win Rate: 98.8%
- Kalshi Fee: 7%

---

## 🎯 **Results Summary**

### **Max Drawdown by Configuration**

| Kelly Fraction | Bet Cap | Max Drawdown | Sharpe Ratio |
|----------------|---------|--------------|--------------|
| **0.50** | **15%** | **-39.1%** | 51.70 |
| 0.50 | 20% | -49.3% | 52.28 |
| 0.50 | 25% | -59.0% | 53.30 |
| 0.50 | 30% | -67.3% | 54.19 |
| 0.75 | 15% | -41.3% | 50.20 |
| 0.75 | 20% | -51.1% | 51.37 |
| 0.75 | 25% | -60.3% | 51.95 |
| 0.75 | 30% | -68.6% | 52.28 |
| 1.00 | 15% | -43.5% | 48.33 |
| 1.00 | 20% | -53.0% | 50.20 |
| 1.00 | 25% | -61.8% | 51.15 |
| 1.00 | 30% | -69.8% | 51.70 |

---

## 🏆 **Recommendations**

### **1. Current Configuration (Conservative)**
```yaml
kelly_fraction: 0.5              # Half-Kelly
max_bet_pct_of_bankroll: 0.15    # 15% max per bet
```

**Performance:**
- Max Drawdown: **-39.1%** ✅ (LOWEST)
- Sharpe Ratio: 51.70
- Risk Level: **Conservative**

**Pros:**
- Lowest maximum drawdown
- Most capital-preserving
- Good for risk-averse traders
- Survives losing streaks better

**Cons:**
- Slightly lower Sharpe than higher caps
- Slower growth (still astronomical with 98.8% win rate)

---

### **2. Balanced (Recommended)**
```yaml
kelly_fraction: 0.5              # Half-Kelly
max_bet_pct_of_bankroll: 0.20    # 20% max per bet
```

**Performance:**
- Max Drawdown: **-49.3%**
- Sharpe Ratio: 52.28
- Risk Level: **Moderate**

**Pros:**
- Better Sharpe ratio than 15% cap
- Still relatively conservative
- Only 10% higher drawdown than current

**Cons:**
- Nearly 50% max drawdown (significant)
- Requires strong risk tolerance

---

### **3. Aggressive (Max Sharpe)**
```yaml
kelly_fraction: 0.5              # Half-Kelly
max_bet_pct_of_bankroll: 0.30    # 30% max per bet
```

**Performance:**
- Max Drawdown: **-67.3%**
- Sharpe Ratio: **54.19** ✅ (HIGHEST)
- Risk Level: **Aggressive**

**Pros:**
- Best risk-adjusted returns (Sharpe)
- Maximum growth potential

**Cons:**
- Nearly 70% max drawdown (extreme)
- Requires very strong risk tolerance
- Large swings in bankroll

---

## 📈 **Key Insights**

### **1. Full Kelly Too Risky**
- Full Kelly (1.0) has worse Sharpe and higher drawdowns
- Half-Kelly (0.5) provides better risk-adjusted returns
- **Recommendation: Stick with Half-Kelly**

### **2. Bet Cap Impact**
- 15% cap: -39.1% max drawdown (safest)
- 20% cap: -49.3% max drawdown (+10% increase)
- 25% cap: -59.0% max drawdown (+20% increase)
- 30% cap: -67.3% max drawdown (+28% increase)

**Each 5% increase in cap adds ~10% to max drawdown**

### **3. Sharpe Ratio Sweet Spot**
- Best Sharpe: Half-Kelly with 30% cap (54.19)
- 2nd Best: Half-Kelly with 25% cap (53.30)
- 3rd Best: Half-Kelly with 20% cap (52.28)

**Higher caps improve Sharpe but increase drawdown significantly**

---

## 🎲 **Risk Tolerance Guide**

### **Conservative Trader**
- **Kelly: 0.5, Cap: 15%**
- Max Drawdown: -39.1%
- "I want to preserve capital and can't stomach >40% drawdowns"

### **Moderate Trader**
- **Kelly: 0.5, Cap: 20%**
- Max Drawdown: -49.3%
- "I can handle ~50% drawdowns for better returns"

### **Aggressive Trader**
- **Kelly: 0.5, Cap: 25-30%**
- Max Drawdown: -59% to -67%
- "I want maximum growth and can handle 60%+ swings"

---

## ⚠️ **Important Notes**

### **Simulation Caveats**

1. **Historical Performance**
   - Based on 10,472 past markets
   - 98.8% win rate may not persist
   - Past performance ≠ future results

2. **Sequential Betting**
   - Simulation assumes sequential market betting
   - Real trading may have concurrent positions
   - Drawdowns could be different with overlapping bets

3. **Market Conditions**
   - Assumes markets remain similar
   - Kalshi fee structure stays at 7%
   - High-probability markets continue to exist

4. **Extreme Returns**
   - Simulation shows astronomical returns due to compounding
   - These are theoretical (10^40+ multipliers)
   - Focus on drawdown and Sharpe metrics instead

### **Real-World Considerations**

1. **Liquidity**
   - May not be able to get full position at desired price
   - Slippage could reduce actual returns

2. **Market Limits**
   - Kalshi has position size limits per market
   - Can't always deploy full Kelly allocation

3. **Psychological**
   - 60%+ drawdowns are psychologically difficult
   - Many traders abandon strategy during drawdowns
   - Conservative approach may be more sustainable

---

## 💡 **Final Recommendation**

**Keep current conservative settings:**
```yaml
kelly_fraction: 0.5              # Half-Kelly
max_bet_pct_of_bankroll: 0.15    # 15% max
```

**Why:**
- Lowest max drawdown (-39.1%)
- Still excellent Sharpe (51.70)
- Sustainable long-term
- Room to increase if desired

**Optional: Increase to 20% cap if:**
- You have strong risk tolerance
- You can handle ~50% drawdowns
- You want +0.5 Sharpe improvement
- You're willing to accept 10% more drawdown

**Do NOT go above 25% cap unless:**
- You have extreme risk tolerance
- You can psychologically handle 60%+ swings
- You're betting with "house money"
- You're very confident in the 98.8% win rate persisting

---

## 📊 **Visualizations**

Simulation generated two charts:
1. `kelly_simulation_results.png` - Growth curves over time
2. `kelly_heatmaps.png` - Return and drawdown heatmaps

These show the exponential growth and drawdown patterns for each configuration.

---

## 🔍 **Methodology**

**Kelly Formula:**
```
Kelly % = (p * b - q) / b

where:
  p = win probability (from backtest accuracy)
  q = 1 - p (loss probability)
  b = payout odds = (1 - price) / price
```

**Position Sizing:**
1. Calculate optimal Kelly fraction for each market
2. Multiply by Kelly multiplier (0.5, 0.75, or 1.0)
3. Cap at max_bet_pct_of_bankroll (15%, 20%, 25%, or 30%)
4. Minimum bet: $1 (Kalshi requirement)

**Drawdown Calculation:**
- Track peak bankroll at each step
- Drawdown = (current - peak) / peak
- Max drawdown = worst drawdown across entire simulation

**Sharpe Ratio:**
- Sharpe = mean(returns) / std(returns) * sqrt(n)
- Measures risk-adjusted performance
- Higher is better

---

This simulation provides data-driven guidance for risk management. Choose parameters based on your risk tolerance and capital preservation goals.
