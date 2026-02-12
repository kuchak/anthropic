#!/bin/bash
#
# Stop the Kalshi Trading Bot
#

echo "🛑 Stopping Kalshi trading bot..."

# Find and kill the bot process
if pkill -f 'python3 main.py'; then
    echo "✅ Bot stopped successfully"
else
    echo "⚠️  No running bot process found"
    echo ""
    echo "Check if bot is running:"
    echo "  ps aux | grep 'python3 main.py'"
fi
