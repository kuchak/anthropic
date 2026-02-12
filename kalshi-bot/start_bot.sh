#!/bin/bash
#
# Kalshi Trading Bot Startup Script
# Runs the bot in background mode with nohup
#

# Check if API credentials are set
if [ -z "$KALSHI_API_KEY_ID" ]; then
    echo "❌ Error: KALSHI_API_KEY_ID not set"
    echo ""
    echo "Please set your API credentials:"
    echo "  export KALSHI_API_KEY_ID='your-key-id'"
    echo "  export KALSHI_PRIVATE_KEY_PATH='/path/to/private_key.pem'"
    echo ""
    echo "Get your API keys at:"
    echo "  Demo: https://demo.kalshi.com/account/profile"
    echo "  Prod: https://kalshi.com/account/profile"
    exit 1
fi

if [ -z "$KALSHI_PRIVATE_KEY_PATH" ]; then
    echo "❌ Error: KALSHI_PRIVATE_KEY_PATH not set"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p ../data

# Start the bot
echo "🚀 Starting Kalshi trading bot..."
echo "   Mode: dry-run (paper trading)"
echo "   Log file: ../data/bot_output.log"
echo ""

cd "$(dirname "$0")"
nohup python3 main.py > ../data/bot_output.log 2>&1 &

PID=$!
echo "✅ Bot started with PID: $PID"
echo ""
echo "📊 Monitor the bot:"
echo "   tail -f ../data/bot_output.log"
echo ""
echo "🛑 Stop the bot:"
echo "   kill $PID"
echo "   # or: pkill -f 'python3 main.py'"
echo ""
echo "✓ The bot will keep running even after you close this terminal"
