"""
Debug script to examine specific markets in detail
"""
import json

# Load the analysis results
with open('tennis_90_accuracy_analysis.json', 'r') as f:
    data = json.load(f)

tickers = ['KXATPMATCH-26FEB09DZUDEL-DZU', 'KXATPMATCH-26FEB08BOOGRE-BOO']

print("="*70)
print("INVESTIGATING DISPUTED MARKETS")
print("="*70)

for ticker in tickers:
    print(f"\n{'='*70}")
    print(f"Market: {ticker}")
    print('='*70)

    for m in data['markets']:
        if m['ticker'] == ticker:
            print(f"\nMarket Info:")
            print(f"  Title: {m['title']}")
            print(f"  Result: {m['result']}")
            print(f"  Settlement: {m['settlement_value']}¢")
            print(f"  Close time: {m['close_time']}")
            print(f"  Total trades analyzed: {m['trades_count']}")

            print(f"\nCrossing Analysis:")
            print(f"  Crossed 90%: {m['crossed_90']}")

            if m.get('first_touch'):
                ft = m['first_touch']
                print(f"\n  First Touch:")
                print(f"    Timestamp: {ft['timestamp']}")
                print(f"    Price: {ft['price']}¢")
                print(f"    Trade index: {ft.get('index', 'N/A')}")

            if m.get('permanent_crossing'):
                pc = m['permanent_crossing']
                print(f"\n  Permanent Crossing:")
                print(f"    Timestamp: {pc['timestamp']}")
                print(f"    Price: {pc['price']}¢")
                print(f"    Trade index: {pc.get('index', 'N/A')}")
                if 'last_below_90' in pc:
                    lb = pc['last_below_90']
                    print(f"    Last below 90¢:")
                    print(f"      Timestamp: {lb['timestamp']}")
                    print(f"      Price: {lb['price']}¢")
            else:
                print(f"\n  NO Permanent Crossing")
                print(f"    (Price came back down after first touch)")

            print(f"\n  Stayed above 90%: {m.get('stayed_above_90', False)}")

            break

print("\n" + "="*70)
print("QUESTION FOR USER:")
print("="*70)
print("""
How are you verifying these prices?
1. Kalshi website charts?
2. API endpoint?
3. Different data source?

Please share what you're seeing so I can debug the discrepancy.
""")
