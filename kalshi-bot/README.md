# Kalshi Trading Bot

Automated trading bot for Kalshi prediction markets with paper trading (dry-run) mode.

## 🔐 Getting Started - API Authentication

### Step 1: Get Your API Keys

You have two options:

#### Option A: Demo API (Recommended for Testing)
- **No real money risk**
- Create account at: https://demo.kalshi.com
- Get API keys at: https://demo.kalshi.com/account/profile

#### Option B: Production API (Real Money)
- **Real money trading**
- Use your main account at: https://kalshi.com
- Get API keys at: https://kalshi.com/account/profile

### Step 2: Generate API Key

1. Go to your account profile page (demo or production)
2. Navigate to "API Keys" section
3. Click "Create New API Key"
4. **Download the private key file immediately** (you cannot retrieve it later!)
5. Save your **Key ID** (shown in the dashboard)

### Step 3: Set Environment Variables

```bash
export KALSHI_API_KEY_ID='your_key_id_here'
export KALSHI_PRIVATE_KEY_PATH='/path/to/your/private_key.pem'
```

Example:
```bash
export KALSHI_API_KEY_ID='abc123def456'
export KALSHI_PRIVATE_KEY_PATH='/home/user/.kalshi/private_key.pem'
```

### Step 4: Configure API Endpoint

Edit `config.yaml` to use demo or production:

```yaml
# Demo API (safe for testing)
kalshi_api_base: "https://demo-api.kalshi.co/trade-api/v2"

# OR Production API (real money!)
# kalshi_api_base: "https://trading-api.kalshi.com/trade-api/v2"
```

### Step 5: Test Authentication

```bash
python3 test_auth.py
```

You should see:
```
✅ ALL TESTS PASSED - API authentication and connection working!
```

---

## 📦 Project Structure

```
kalshi-bot/
├── config.yaml              # Configuration (API, risk management, etc.)
├── models.py                # Data classes (Market, Trade, Portfolio)
├── logger_setup.py          # Structured logging
├── kalshi_client.py         # API client with RSA signing
├── test_auth.py             # Authentication test script
├── scanner.py               # Market discovery (TODO)
├── scorer.py                # Opportunity scoring (TODO)
├── allocator.py             # Position sizing (TODO)
├── executor.py              # Trade execution (TODO)
├── tracker.py               # Portfolio tracking (TODO)
├── main.py                  # Main orchestration loop (TODO)
└── data/                    # Trade history, settlements, etc.
```

---

## ✅ Module Status

- ✅ **Module 1: API Client** - Complete with RSA authentication
- ⏳ **Module 2: Scanner** - Pending
- ⏳ **Module 3: Scorer** - Pending
- ⏳ **Module 4: Allocator** - Pending
- ⏳ **Module 5: Executor** - Pending
- ⏳ **Module 6: Tracker** - Pending
- ⏳ **Module 7: Main Loop** - Pending

---

## 🔒 Security Notes

- **Never commit your private key to git**
- Store private keys securely (e.g., `~/.kalshi/`)
- Use demo API for all testing
- Only switch to production after thorough validation
- Start with small bankroll in production

---

## 📚 Resources

- **Kalshi API Documentation**: https://docs.kalshi.com
- **Demo Account**: https://demo.kalshi.com
- **Production Account**: https://kalshi.com

---

## 🚀 Next Steps

Once authentication test passes:
1. Build scanner module (market discovery)
2. Build scorer module (opportunity ranking)
3. Build allocator module (Kelly criterion sizing)
4. Build executor module (dry-run/live trading)
5. Build tracker module (P&L and settlements)
6. Build main loop (orchestration)
