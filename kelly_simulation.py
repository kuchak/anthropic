"""
Kelly Criterion Simulation using REAL backtest data
Tests different Kelly fractions and bet caps to find optimal parameters
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

print("=" * 80)
print("KELLY CRITERION SIMULATION")
print("=" * 80)
print()

# Load backtest data
csv_file = '/home/user/anthropic/comprehensive_crossed_90_detailed.csv'
df = pd.read_csv(csv_file)

print(f"✅ Loaded {len(df)} markets from backtest")
print()

# Filter to markets with price and result data
df_clean = df[df['Permanent Cross Price (¢)'].notna()].copy()
df_clean['price'] = df_clean['Permanent Cross Price (¢)'] / 100

# Only use markets in our target range (0.50-0.98)
df_clean = df_clean[(df_clean['price'] >= 0.50) & (df_clean['price'] <= 0.98)]

# Determine wins
df_clean['won'] = df_clean['Prediction Correct'] == 'CORRECT'

print(f"📊 Markets in target range (50-98¢): {len(df_clean)}")
print(f"   Wins: {df_clean['won'].sum()}")
print(f"   Losses: {(~df_clean['won']).sum()}")
print(f"   Win Rate: {df_clean['won'].mean() * 100:.1f}%")
print()

# Assign accuracy by price range (from our config)
def get_win_probability(price):
    if 0.85 <= price <= 0.89:
        return 0.991
    elif 0.90 <= price <= 0.95:
        return 0.990
    elif 0.95 <= price <= 0.98:
        return 0.983
    else:
        return 0.985  # default

df_clean['win_prob'] = df_clean['price'].apply(get_win_probability)

# Calculate Kelly fraction for each bet
# Kelly = (p * b - q) / b
# where p = win probability, q = 1-p, b = odds (payout/stake)
# For Kalshi: if you buy at price p, you win (1-p)/p if it hits

def calculate_kelly_fraction(price, win_prob):
    """Calculate optimal Kelly fraction for a contract"""
    # Payout odds: if you buy at price p and win, you get $1, profit is (1-p)
    # So odds b = (1-p) / p
    if price >= 0.99:
        return 0  # Too expensive, no edge

    b = (1 - price) / price  # payout odds
    p = win_prob
    q = 1 - p

    kelly = (p * b - q) / b

    return max(0, kelly)  # Can't be negative

df_clean['kelly_fraction'] = df_clean.apply(
    lambda row: calculate_kelly_fraction(row['price'], row['win_prob']),
    axis=1
)

print("📈 Kelly Fraction Distribution:")
print(f"   Mean: {df_clean['kelly_fraction'].mean():.3f}")
print(f"   Median: {df_clean['kelly_fraction'].median():.3f}")
print(f"   Min: {df_clean['kelly_fraction'].min():.3f}")
print(f"   Max: {df_clean['kelly_fraction'].max():.3f}")
print()

# Sort by timestamp to simulate sequential betting
if 'Permanent Cross Time' in df_clean.columns:
    df_clean['timestamp'] = pd.to_datetime(df_clean['Permanent Cross Time'])
    df_clean = df_clean.sort_values('timestamp')
    print("✅ Sorted by timestamp (sequential betting simulation)")
else:
    print("⚠️  No timestamp, using random order")

print()

# Simulation parameters
STARTING_BANKROLL = 1000.0
KELLY_FRACTIONS = [0.5, 0.75, 1.0]  # Half-Kelly, 3/4-Kelly, Full-Kelly
BET_CAPS = [0.15, 0.20, 0.25, 0.30]  # Max % of bankroll per bet
KALSHI_FEE = 0.07  # 7% taker fee

print("🎲 SIMULATION PARAMETERS")
print("=" * 80)
print(f"Starting Bankroll: ${STARTING_BANKROLL:,.2f}")
print(f"Kelly Fractions: {KELLY_FRACTIONS}")
print(f"Bet Caps: {BET_CAPS}")
print(f"Kalshi Fee: {KALSHI_FEE * 100:.0f}%")
print(f"Markets: {len(df_clean)}")
print()

# Run simulations
results = []

for kelly_mult in KELLY_FRACTIONS:
    for bet_cap in BET_CAPS:

        bankroll = STARTING_BANKROLL
        bankroll_history = [bankroll]
        max_bankroll = bankroll

        for idx, row in df_clean.iterrows():
            price = row['price']
            win_prob = row['win_prob']
            kelly = row['kelly_fraction']
            won = row['won']

            # Calculate bet size
            raw_kelly_bet = kelly * kelly_mult * bankroll
            capped_bet = min(raw_kelly_bet, bet_cap * bankroll)

            # Minimum bet is $1
            if capped_bet < 1.0:
                capped_bet = 0  # Skip if can't meet minimum

            if capped_bet == 0:
                bankroll_history.append(bankroll)
                continue

            # Calculate number of contracts
            # For simplicity, assume we can buy fractional contracts
            contracts = capped_bet / price

            # Calculate fee
            # Fee = 0.07 * contracts * price * (1 - price)
            fee = KALSHI_FEE * contracts * price * (1 - price)

            # Outcome
            if won:
                # Win: get $1 per contract, minus what we paid
                profit = contracts * (1 - price) - fee
                bankroll += profit
            else:
                # Loss: lose what we paid plus fee
                loss = contracts * price + fee
                bankroll -= loss

            # Track max for drawdown calculation
            if bankroll > max_bankroll:
                max_bankroll = bankroll

            bankroll_history.append(bankroll)

            # Check if busted
            if bankroll <= 0:
                bankroll = 0.01  # Keep a penny to continue tracking

        # Calculate metrics
        final_bankroll = bankroll
        total_return = (final_bankroll / STARTING_BANKROLL - 1) * 100

        # Max drawdown
        bankroll_array = np.array(bankroll_history)
        peak = np.maximum.accumulate(bankroll_array)
        drawdown = (bankroll_array - peak) / peak
        max_drawdown = drawdown.min() * 100

        # Sharpe-like metric (return / volatility)
        returns = np.diff(bankroll_array) / bankroll_array[:-1]
        if len(returns) > 0 and returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(len(returns))
        else:
            sharpe = 0

        results.append({
            'kelly_fraction': kelly_mult,
            'bet_cap': bet_cap,
            'final_bankroll': final_bankroll,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_drawdown,
            'sharpe': sharpe,
            'bankroll_history': bankroll_history
        })

        print(f"Kelly {kelly_mult:.2f}, Cap {bet_cap:.0%}: "
              f"${final_bankroll:,.0f} ({total_return:+.1f}%), "
              f"Max DD: {max_drawdown:.1f}%")

print()
print("=" * 80)
print("📊 RESULTS SUMMARY")
print("=" * 80)
print()

# Sort by total return
results_df = pd.DataFrame([{
    'Kelly Fraction': r['kelly_fraction'],
    'Bet Cap': f"{r['bet_cap']:.0%}",
    'Final Bankroll': f"${r['final_bankroll']:,.0f}",
    'Return': f"{r['total_return_pct']:+.1f}%",
    'Max Drawdown': f"{r['max_drawdown_pct']:.1f}%",
    'Sharpe': f"{r['sharpe']:.2f}"
} for r in results])

print(results_df.to_string(index=False))
print()

# Find best by return
best_return = max(results, key=lambda x: x['total_return_pct'])
print(f"🏆 Best Return: Kelly {best_return['kelly_fraction']:.2f}, "
      f"Cap {best_return['bet_cap']:.0%} → "
      f"${best_return['final_bankroll']:,.0f} ({best_return['total_return_pct']:+.1f}%)")
print()

# Find best by Sharpe
best_sharpe = max(results, key=lambda x: x['sharpe'])
print(f"📈 Best Risk-Adjusted: Kelly {best_sharpe['kelly_fraction']:.2f}, "
      f"Cap {best_sharpe['bet_cap']:.0%} → "
      f"${best_sharpe['final_bankroll']:,.0f} ({best_sharpe['total_return_pct']:+.1f}%), "
      f"Sharpe {best_sharpe['sharpe']:.2f}")
print()

# Plot growth curves
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Plot 1: Growth curves by Kelly fraction (using 20% cap)
ax1.set_title('Bankroll Growth by Kelly Fraction (20% Bet Cap)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Market Number')
ax1.set_ylabel('Bankroll ($)')
ax1.grid(True, alpha=0.3)
ax1.axhline(y=STARTING_BANKROLL, color='gray', linestyle='--', alpha=0.5, label='Starting Bankroll')

for result in results:
    if result['bet_cap'] == 0.20:  # Only show 20% cap
        label = f"Kelly {result['kelly_fraction']:.2f} ({result['total_return_pct']:+.1f}%, DD: {result['max_drawdown_pct']:.1f}%)"
        ax1.plot(result['bankroll_history'], label=label, linewidth=2)

ax1.legend()

# Plot 2: Growth curves by bet cap (using 0.5 Kelly)
ax2.set_title('Bankroll Growth by Bet Cap (Half-Kelly)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Market Number')
ax2.set_ylabel('Bankroll ($)')
ax2.grid(True, alpha=0.3)
ax2.axhline(y=STARTING_BANKROLL, color='gray', linestyle='--', alpha=0.5, label='Starting Bankroll')

for result in results:
    if result['kelly_fraction'] == 0.5:  # Only show half-Kelly
        label = f"Cap {result['bet_cap']:.0%} ({result['total_return_pct']:+.1f}%, DD: {result['max_drawdown_pct']:.1f}%)"
        ax2.plot(result['bankroll_history'], label=label, linewidth=2)

ax2.legend()

plt.tight_layout()
plt.savefig('kelly_simulation_results.png', dpi=150, bbox_inches='tight')
print("📊 Saved growth curves to: kelly_simulation_results.png")
print()

# Create heatmap of returns
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Heatmap 1: Total Return
returns_matrix = np.zeros((len(KELLY_FRACTIONS), len(BET_CAPS)))
for i, kelly in enumerate(KELLY_FRACTIONS):
    for j, cap in enumerate(BET_CAPS):
        result = next(r for r in results if r['kelly_fraction'] == kelly and r['bet_cap'] == cap)
        returns_matrix[i, j] = result['total_return_pct']

im1 = axes[0].imshow(returns_matrix, cmap='RdYlGn', aspect='auto')
axes[0].set_xticks(range(len(BET_CAPS)))
axes[0].set_yticks(range(len(KELLY_FRACTIONS)))
axes[0].set_xticklabels([f"{c:.0%}" for c in BET_CAPS])
axes[0].set_yticklabels([f"{k:.2f}" for k in KELLY_FRACTIONS])
axes[0].set_xlabel('Bet Cap', fontweight='bold')
axes[0].set_ylabel('Kelly Fraction', fontweight='bold')
axes[0].set_title('Total Return (%)', fontsize=14, fontweight='bold')

# Add values to cells
for i in range(len(KELLY_FRACTIONS)):
    for j in range(len(BET_CAPS)):
        text = axes[0].text(j, i, f"{returns_matrix[i, j]:.1f}%",
                           ha="center", va="center", color="black", fontsize=10)

plt.colorbar(im1, ax=axes[0], label='Return (%)')

# Heatmap 2: Max Drawdown
dd_matrix = np.zeros((len(KELLY_FRACTIONS), len(BET_CAPS)))
for i, kelly in enumerate(KELLY_FRACTIONS):
    for j, cap in enumerate(BET_CAPS):
        result = next(r for r in results if r['kelly_fraction'] == kelly and r['bet_cap'] == cap)
        dd_matrix[i, j] = abs(result['max_drawdown_pct'])

im2 = axes[1].imshow(dd_matrix, cmap='RdYlGn_r', aspect='auto')  # Reversed colormap (red = bad)
axes[1].set_xticks(range(len(BET_CAPS)))
axes[1].set_yticks(range(len(KELLY_FRACTIONS)))
axes[1].set_xticklabels([f"{c:.0%}" for c in BET_CAPS])
axes[1].set_yticklabels([f"{k:.2f}" for k in KELLY_FRACTIONS])
axes[1].set_xlabel('Bet Cap', fontweight='bold')
axes[1].set_ylabel('Kelly Fraction', fontweight='bold')
axes[1].set_title('Max Drawdown (%)', fontsize=14, fontweight='bold')

# Add values to cells
for i in range(len(KELLY_FRACTIONS)):
    for j in range(len(BET_CAPS)):
        text = axes[1].text(j, i, f"{dd_matrix[i, j]:.1f}%",
                           ha="center", va="center", color="black", fontsize=10)

plt.colorbar(im2, ax=axes[1], label='Max Drawdown (%)')

plt.tight_layout()
plt.savefig('kelly_heatmaps.png', dpi=150, bbox_inches='tight')
print("📊 Saved heatmaps to: kelly_heatmaps.png")
print()

print("=" * 80)
print("✅ SIMULATION COMPLETE")
print("=" * 80)
print()

print("🎯 RECOMMENDATIONS:")
print()

# Find best balance of return and drawdown
# Score = return / abs(drawdown)
best_balanced = max(results, key=lambda x: x['total_return_pct'] / abs(x['max_drawdown_pct']))
print(f"Best Risk/Reward Balance:")
print(f"  Kelly Fraction: {best_balanced['kelly_fraction']:.2f}")
print(f"  Bet Cap: {best_balanced['bet_cap']:.0%}")
print(f"  Return: {best_balanced['total_return_pct']:+.1f}%")
print(f"  Max Drawdown: {best_balanced['max_drawdown_pct']:.1f}%")
print(f"  Sharpe: {best_balanced['sharpe']:.2f}")
print()

print("Conservative (minimize drawdown):")
best_safe = min(results, key=lambda x: abs(x['max_drawdown_pct']))
print(f"  Kelly Fraction: {best_safe['kelly_fraction']:.2f}")
print(f"  Bet Cap: {best_safe['bet_cap']:.0%}")
print(f"  Return: {best_safe['total_return_pct']:+.1f}%")
print(f"  Max Drawdown: {best_safe['max_drawdown_pct']:.1f}%")
print()

print("Aggressive (maximize return):")
print(f"  Kelly Fraction: {best_return['kelly_fraction']:.2f}")
print(f"  Bet Cap: {best_return['bet_cap']:.0%}")
print(f"  Return: {best_return['total_return_pct']:+.1f}%")
print(f"  Max Drawdown: {best_return['max_drawdown_pct']:.1f}%")
print()
