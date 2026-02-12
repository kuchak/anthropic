# Running the Kalshi Trading Bot

## 🚀 Quick Start

### 1. Set API Credentials

**For Demo API (recommended for testing):**
```bash
export KALSHI_API_KEY_ID='your-demo-api-key-id'
export KALSHI_PRIVATE_KEY_PATH='/path/to/demo_private_key.pem'
```

**For Production API:**
```bash
export KALSHI_API_KEY_ID='your-prod-api-key-id'
export KALSHI_PRIVATE_KEY_PATH='/path/to/prod_private_key.pem'
```

**Get API keys:**
- Demo: https://demo.kalshi.com/account/profile
- Production: https://kalshi.com/account/profile

---

### 2. Start the Bot

```bash
cd kalshi-bot
./start_bot.sh
```

This will:
- ✅ Start the bot in background mode (keeps running after terminal closes)
- ✅ Log all output to `../data/bot_output.log`
- ✅ Run in dry-run mode (paper trading, no real money)

**Expected output:**
```
🚀 Starting Kalshi trading bot...
   Mode: dry-run (paper trading)
   Log file: ../data/bot_output.log

✅ Bot started with PID: 12345

📊 Monitor the bot:
   tail -f ../data/bot_output.log

🛑 Stop the bot:
   kill 12345
   # or: pkill -f 'python3 main.py'

✓ The bot will keep running even after you close this terminal
```

---

### 3. Monitor the Bot

**View live output:**
```bash
cd kalshi-bot
./monitor_bot.sh
```

**Or manually:**
```bash
tail -f data/bot_output.log
```

**View last 50 lines:**
```bash
tail -50 data/bot_output.log
```

**Search logs for specific events:**
```bash
grep "Trade executed" data/bot_output.log
grep "ERROR" data/bot_output.log
grep "opportunity" data/bot_output.log
```

---

### 4. Stop the Bot

**Using the stop script:**
```bash
cd kalshi-bot
./stop_bot.sh
```

**Or manually:**
```bash
# Find the process ID
ps aux | grep 'python3 main.py'

# Kill by PID
kill <PID>

# Or kill all instances
pkill -f 'python3 main.py'
```

---

## 📊 What the Bot Does

### Scanning Cycle

1. **Slow Scan (every 15 minutes)**
   - Fetches all open markets from Kalshi
   - Filters by price range (85-98¢)
   - Filters by settlement time (5 min - 6 hours)
   - Builds watchlist of opportunities

2. **Fast Scan (every 3 minutes)**
   - Updates prices for watchlist markets
   - Removes markets that no longer qualify
   - Removes markets where we have positions

3. **Scoring & Ranking**
   - Calculates win probability by price range
   - Applies category accuracy override (Entertainment/Financials)
   - Calculates expected profit after fees
   - Ranks by expected profit / time to settlement

4. **Position Sizing**
   - Uses Half-Kelly criterion (0.5)
   - Max 15% of bankroll per bet
   - Max 70% total exposure
   - Minimum $1 per bet (Kalshi requirement)

5. **Execution (DRY RUN)**
   - In dry-run mode: Logs what it WOULD do
   - In live mode: Places actual trades

---

## 🔍 Understanding the Logs

### Normal Operation

```
Scanner initialized
  NO CATEGORY FILTERING - evaluating ALL markets
  Price range: $0.85 - $0.98
  Settlement window: 5m - 6h

🔍 Starting slow scan (full market discovery)...
  Retrieved 1247 total open markets
✅ Slow scan complete
  Watchlist: 23 markets (was 0)

Scored 23 markets → 18 valid opportunities

Top 5 Opportunities:
  1. KXSPORTS-GAME123-YES @ $0.87 → ROI: 12.3%, Exp Profit: $0.11
  2. KXCRYPTO-BTC456-YES @ $0.92 → ROI: 7.8%, Exp Profit: $0.07
  ...
```

### Position Sizing

```
[DRY RUN] Would allocate positions:
  KXSPORTS-GAME123-YES: $150 (15.0% of bankroll)
    - Entry: $0.87
    - Expected profit: $16.50
    - Win probability: 99.1%
    - Kelly fraction: 0.85 → capped at 15%
```

### Errors to Watch For

```
❌ Error: Rate limit exceeded
→ Bot will back off and retry

❌ Error: Insufficient liquidity
→ Bot will skip this market

⚠️  Category override: Entertainment @ $0.87
    Using 89.3% accuracy (not 99.1%)
→ Normal behavior, protecting against risky category
```

---

## ⚙️ Configuration

Edit `config.yaml` to adjust:

### Trading Parameters
```yaml
min_contract_price: 0.85        # Only 85¢+ contracts
max_contract_price: 0.98        # Skip 98¢+ (too little edge)
max_time_to_settlement_hours: 6 # Settlement window
```

### Position Sizing
```yaml
kelly_fraction: 0.5              # Half-Kelly (conservative)
max_bet_pct_of_bankroll: 0.15    # 15% max per bet
max_total_exposure_pct: 0.70     # 70% max total
```

### Risk Management
```yaml
max_daily_loss: 100.00           # Stop if lose $100/day
max_consecutive_losses: 5        # Pause after 5 losses
max_trades_per_day: 50           # Circuit breaker
```

---

## 🔐 Switching from Demo to Production

**⚠️ IMPORTANT: Only switch to production after thorough testing!**

1. **Update API credentials:**
   ```bash
   export KALSHI_API_KEY_ID='your-PRODUCTION-key-id'
   export KALSHI_PRIVATE_KEY_PATH='/path/to/PRODUCTION_private_key.pem'
   ```

2. **Update config.yaml:**
   ```yaml
   # Change this
   dry_run: true
   kalshi_api_base: "https://demo-api.kalshi.co/trade-api/v2"

   # To this
   dry_run: false  # ⚠️ REAL MONEY
   kalshi_api_base: "https://trading-api.kalshi.com/trade-api/v2"
   ```

3. **Start with small bankroll:**
   ```yaml
   starting_bankroll: 100.00  # Start small!
   ```

4. **Monitor closely for first 24 hours**

---

## 🐛 Troubleshooting

### Bot won't start

**Check API credentials:**
```bash
echo $KALSHI_API_KEY_ID
echo $KALSHI_PRIVATE_KEY_PATH
ls -la $KALSHI_PRIVATE_KEY_PATH  # File should exist
```

**Check log file:**
```bash
cat data/bot_output.log
```

### Bot stopped unexpectedly

**Check if it's still running:**
```bash
ps aux | grep 'python3 main.py'
```

**Check logs for errors:**
```bash
tail -100 data/bot_output.log | grep ERROR
```

**Common causes:**
- API credentials expired
- Network connection lost
- Hit daily loss limit
- Hit consecutive loss limit
- Python exception (check logs)

### No opportunities found

**This is normal if:**
- No markets in 85-98¢ range
- No markets settling in 5min-6hr window
- All markets have existing positions
- Category override discounting all opportunities

**Check watchlist size:**
```bash
grep "Watchlist:" data/bot_output.log | tail -5
```

---

## 📁 Important Files

```
kalshi-bot/
├── start_bot.sh           # Start bot in background
├── stop_bot.sh            # Stop the bot
├── monitor_bot.sh         # Monitor live output
├── config.yaml            # Bot configuration
├── main.py               # Main bot logic
└── RUNNING_THE_BOT.md    # This file

data/
└── bot_output.log        # All bot logs
```

---

## 🎯 Best Practices

### Testing
1. ✅ Always test on demo API first
2. ✅ Run in dry-run mode for at least 24 hours
3. ✅ Verify accuracy data matches expectations
4. ✅ Check that position sizing is correct

### Monitoring
1. ✅ Check logs daily for errors
2. ✅ Monitor bankroll growth/drawdown
3. ✅ Verify trades match expected behavior
4. ✅ Watch for category override warnings

### Risk Management
1. ✅ Start with small bankroll
2. ✅ Keep max_bet_pct_of_bankroll at 15% or lower
3. ✅ Set max_daily_loss to acceptable amount
4. ✅ Don't disable safety features (loss limits, etc.)

### Production
1. ✅ Never run multiple instances simultaneously
2. ✅ Keep API keys secure (don't commit to git)
3. ✅ Backup logs regularly
4. ✅ Monitor Kalshi account independently

---

## 📞 Support

**Issues with the bot:**
- Check logs first: `tail -100 data/bot_output.log`
- Review configuration: `cat config.yaml`
- Test API credentials: Try accessing Kalshi website

**Issues with Kalshi API:**
- Demo API: https://demo.kalshi.com/support
- Production API: https://kalshi.com/support
- API docs: https://trading-api.readme.io/

---

**Remember: This bot trades real money (in production mode). Always test thoroughly in demo mode first!**
