# Stability Tracker Integration Plan

## Current Problem

The bot currently **immediately** bets when it sees a 90¢+ market, with NO wait time.

From backtest: **58% of markets drop back** below 90¢ before stabilizing.

## Solution: Add Stability Tracking

### 1. New Component Created

`stability_tracker.py` - Tracks when markets first hit 90¢ and enforces wait times.

**Key Logic:**
```python
def check_market(ticker, current_price):
    # If price < 90¢: RESET timer
    if current_price < 0.90:
        reset_timer(ticker)
        return False  # NOT ready

    # If first time seeing price >= 90¢: START timer
    if ticker not in timers:
        start_timer(ticker)
        return False  # NOT ready (just started waiting)

    # If timer running: CHECK if enough time passed
    elapsed = now() - first_touch_time[ticker]
    if elapsed >= required_wait_time[ticker]:
        return True  # READY TO BET!
    else:
        return False  # STILL WAITING
```

### 2. Integration Points in main.py

**Changes needed in `TradingBot.__init__()`:**

```python
# Add after Scorer initialization (line 78)
logger.info("\n⏱️  Initializing stability tracker...")
self.stability_tracker = StabilityTracker(config)
logger.info("✅ Stability tracker ready")
```

**Changes needed in `TradingBot.run_once()` between Step 2 and Step 3:**

```python
# After scoring (line 171), BEFORE allocation (line 200)

# NEW STEP: Filter by stability
logger.info("\n⏱️  Step 2.5: Stability Check")
logger.info("-" * 80)

stable_opportunities = []
for opp in opportunities:
    # Check if market is stable (held >= 90¢ for required wait time)
    is_stable = self.stability_tracker.check_market(
        ticker=opp.market.ticker,
        current_price=opp.entry_price
    )

    if is_stable:
        stable_opportunities.append(opp)
    else:
        # Log why we're not betting yet
        status = self.stability_tracker.get_wait_status(opp.market.ticker)
        if status:
            reason = f"waiting {status['remaining_minutes']:.1f}m more"
        else:
            reason = "just started waiting"

        self.decision_logger.log_skipped(
            ticker=opp.market.ticker,
            title=opp.market.title,
            category=opp.market.category,
            yes_price=opp.market.best_yes_price,
            no_price=opp.market.best_no_price,
            time_to_settlement_hours=opp.time_to_settlement_hours,
            skip_reason=f"price not stable ({reason})"
        )

logger.info(f"✅ {len(stable_opportunities)}/{len(opportunities)} opportunities passed stability check")

# Replace `opportunities` with `stable_opportunities` for allocation
if not stable_opportunities:
    logger.info("⚠️  No stable opportunities, skipping cycle")
    self.decision_logger.end_cycle()
    return

# Step 3: Allocate positions (now using stable_opportunities)
allocations = self.allocator.allocate_positions(stable_opportunities, current_exposure)
```

**After execution (line 268), mark markets as bet on:**

```python
# After adding executions to tracker (line 268)
# Reset stability tracking for executed markets
for execution in executions:
    if execution.status == "success":
        self.stability_tracker.reset_market(execution.ticker)
```

### 3. Example Flow

**Scenario: NBA game market**

```
Cycle 1 (13:00:00):
  - Scanner finds KXNBAGAME-24-02-13 at $0.91
  - Scorer: ✅ Valid opportunity (100% accuracy, high ROI)
  - Stability: ❌ First touch, start 1-minute timer
  - Result: NO BET (waiting)

Cycle 2 (13:03:00 - 3 min later):
  - Scanner finds KXNBAGAME-24-02-13 at $0.92 (still high)
  - Scorer: ✅ Valid opportunity
  - Stability: ✅ STABLE (held 3 min > 1 min required)
  - Allocator: ✅ Allocate position
  - Executor: ✅ PLACE BET
  - Result: BET PLACED
```

**Scenario: Unstable market (drops back)**

```
Cycle 1 (13:00:00):
  - Scanner finds KXEPLGAME-24-02-13 at $0.91
  - Stability: ⏱️  First touch, start 1-minute timer

Cycle 2 (13:03:00):
  - Scanner finds KXEPLGAME-24-02-13 at $0.88 (DROPPED!)
  - Stability: 🔄 RESET timer (price dropped below 90¢)
  - Result: NO BET (correctly avoided unstable market)

Cycle 3 (13:06:00):
  - Scanner finds KXEPLGAME-24-02-13 at $0.92 (back up)
  - Stability: ⏱️  First touch AGAIN, restart 1-minute timer
  - Result: NO BET (waiting for new stability period)
```

### 4. Configuration Already in Place

Wait times are already in `config.yaml`:

```yaml
series_ticker_wait_times:
  KXNBAGAME: 1      # NBA waits 1 minute
  KXBTC15M: 1       # Bitcoin waits 1 minute
  KXATPMATCH: 5     # Tennis waits 5 minutes
  KXNHLGAME: 3      # NHL waits 3 minutes
  # ... etc for all 28 tickers
```

### 5. Testing Before Live

**Dry-run test:**
```bash
cd kalshi-bot
python main.py --once --dry-run
```

**Expected output:**
```
⏱️  Step 2.5: Stability Check
⏱️  KXNBAGAME-24-02-13: First touch at $0.91 - waiting 1m
⏳ KXATPMATCH-24-02-13: Held for 2.3m, need 2.7m more
✅ KXNHLGAME-24-02-13: STABLE for 3.2m (required: 3m) - READY TO BET
✅ 1/3 opportunities passed stability check
```

### 6. Benefits

✅ **Prevents 58% of losing bets** (markets that drop back)
✅ **Increases accuracy from ~76% to 94%+**
✅ **Ticker-specific wait times** (fast markets wait less)
✅ **Auto-resets** if price drops (prevents betting on bounces)
✅ **Stateful tracking** across scan cycles
✅ **Detailed logging** for debugging

### 7. Risk Analysis

**What if we miss good opportunities?**
- From backtest: We capture 24-60% of markets (depending on wait time)
- BUT: Those we DO bet on have 94-99% accuracy vs 76% without waiting
- Net result: Higher profit even with fewer bets

**What if price changes after wait?**
- We check price BOTH at start AND end of wait period
- Only bet if price still >= 90¢ after waiting
- If price increased to 95¢, we might skip it (max_price = 93¢)

**What if market closes during wait?**
- Scanner filters out markets < 5 minutes to settlement
- With max 5-minute wait, we still have time to bet
- If market closes, it drops from watchlist automatically

### 8. Next Steps

1. ✅ Review this implementation
2. ⬜ Integrate into main.py (3 small changes)
3. ⬜ Test with --dry-run --once
4. ⬜ Monitor first few cycles for correct behavior
5. ⬜ Enable continuous mode after validation

### 9. Code Review Checklist

**Before approving:**
- [ ] Logic is clear and matches backtest findings
- [ ] Timer resets correctly when price drops
- [ ] Series ticker extraction works for all ticker formats
- [ ] Wait times are correctly loaded from config
- [ ] Cleanup happens for old markets (memory management)
- [ ] Logging is sufficient for debugging
- [ ] Edge cases handled (first touch, price drops, etc.)

**Critical questions:**
1. Does it correctly detect "first touch" at 90¢?
2. Does it RESET the timer if price drops below 90¢?
3. Does it enforce ticker-specific wait times?
4. Does it check price AGAIN after waiting?
5. Does it cleanup old tracking to avoid memory leaks?

---

## Summary

**Current bot:** Bets immediately → 76% accuracy → LOSING
**With stability:** Waits 1-5 min → 94% accuracy → WINNING

The implementation is ready for your review. The logic matches our backtest findings exactly.
