#!/bin/bash
#
# Monitor the Kalshi Trading Bot
#

LOG_FILE="../data/bot_output.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    echo "   Bot may not be running yet"
    exit 1
fi

echo "📊 Monitoring bot output (Ctrl+C to exit)"
echo "   Log file: $LOG_FILE"
echo ""

# Follow the log file
tail -f "$LOG_FILE"
