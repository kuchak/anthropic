# Kalshi Market Backtesting Tool

A production-ready Python script for analyzing the accuracy of Kalshi prediction markets at their **first 90% crossing**.

## Overview

This tool backtests historical Kalshi markets to determine how accurate the market was when it first crossed a 90% probability threshold. It helps answer the question: "When a Kalshi market first hits 90%, how often does that prediction come true?"

## Key Features

- **First Crossing Detection**: Tracks the FIRST time a market crosses 90% (handles jumps from 89% to 93%)
- **Robust Rate Limiting**: Configurable delays and exponential backoff to avoid API bans
- **Batch Processing**: Processes markets in batches with automatic pauses
- **Category Analysis**: Breaks down accuracy by market category
- **Timing Analysis**: Tracks early vs late signals (first/last 50% of market lifetime)
- **CSV Export**: Saves detailed results with timestamps for further analysis

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the script with default settings:

```bash
python kalshi_backtest.py
```

### Configuration

Modify the constants in the `main()` function to customize the analysis:

```python
MAX_MARKETS = 200          # Number of markets to analyze
THRESHOLD = 90             # Probability threshold (90 = 90%)
RATE_LIMIT_DELAY = 1.0     # Seconds between API calls
BATCH_SIZE = 50            # Markets to process before pausing
BATCH_PAUSE = 30           # Pause duration in seconds
PERIOD_INTERVAL = 1440     # Candlestick interval (1=1min, 60=1hr, 1440=1day)
```

## Output

The script provides:

1. **Console Output**: Real-time progress and summary statistics
2. **CSV File**: Detailed results saved as `kalshi_backtest_YYYYMMDD_HHMMSS.csv`

### Sample Output

```
📈 OVERALL RESULTS
======================================================================
Total markets analyzed: 200
Markets that crossed 90%: 45
Correct predictions (resolved YES): 38
⭐ Overall Accuracy: 84.44%

🔹 Early signals (first 50% of market life): 20 markets, 90.00% accurate
🔸 Late signals (last 50% of market life): 25 markets, 80.00% accurate

📊 ACCURACY BY CATEGORY
======================================================================
Category                Hit 90%  Correct  Accuracy  Early  Late
Sports                       25       22    88.0%     12    13
Politics                     15       11    73.3%      6     9
Economics                     5        5   100.0%      2     3
```

## How It Works

1. **Fetch Markets**: Retrieves settled markets from Kalshi API
2. **Get Candlestick Data**: Downloads price history for each market
3. **Find First Crossing**: Identifies the first time price crossed 90%
4. **Calculate Timing**: Determines when crossing occurred (early/late)
5. **Validate**: Compares prediction to actual market outcome
6. **Aggregate**: Calculates accuracy overall and by category

## Rate Limiting

The script includes multiple layers of rate limiting protection:

- Configurable delay between requests (default: 1 second)
- Batch processing with pauses (default: 50 markets, 30s pause)
- Exponential backoff on 429 errors (60s, 120s, 240s)
- Automatic retry logic

## Requirements

- Python 3.7+
- requests
- pandas

## API Documentation

Uses the Kalshi Trade API v2:
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`
- No authentication required for public market data

## License

This is a backtesting tool for educational and research purposes.
