import os
import sys
import yaml
from kalshi_client import KalshiClient

# Source env vars
os.environ['KALSHI_API_KEY_ID'] = '9baba9f8-39c8-48fc-bd23-cb8b2c5cfff8'
os.environ['KALSHI_PRIVATE_KEY_PATH'] = '/home/user/anthropic/kalshi-bot/kalshi_private_key.pem'

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test API connection
print("Testing Kalshi API connection...")
client = KalshiClient(config)

if client.test_connection():
    print("✅ API connection successful")
else:
    print("❌ API connection failed")
