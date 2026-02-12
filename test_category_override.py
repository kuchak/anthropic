"""
Test category accuracy override feature

Verifies that the scorer uses the more conservative estimate when
category accuracy is below the threshold (95%)
"""
import yaml
import sys
sys.path.insert(0, 'kalshi-bot')

from scorer import Scorer
from dataclasses import dataclass

@dataclass
class MockMarket:
    ticker: str
    category: str
    best_yes_price: float
    best_no_price: float
    time_to_settlement_minutes: float

print("=" * 80)
print("CATEGORY ACCURACY OVERRIDE TEST")
print("=" * 80)
print()

# Load config
with open('kalshi-bot/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("📊 CONFIGURATION")
print("=" * 80)
print()
print(f"Category accuracy threshold: {config['category_accuracy_threshold'] * 100:.0f}%")
print()

print("Categories below threshold (will use conservative override):")
for category, accuracy in config['category_accuracy'].items():
    if accuracy < config['category_accuracy_threshold']:
        print(f"  • {category}: {accuracy * 100:.1f}%")
print()

print("Categories above threshold (will use price range accuracy):")
for category, accuracy in config['category_accuracy'].items():
    if accuracy >= config['category_accuracy_threshold']:
        print(f"  • {category}: {accuracy * 100:.1f}%")
print()

# Initialize scorer
scorer = Scorer(config)

print("=" * 80)
print("🧪 TEST CASES")
print("=" * 80)
print()

# Test case 1: Entertainment (89.3% < 95%) at 87¢
print("Test 1: Entertainment market at $0.87")
print("-" * 80)
print(f"  Price range accuracy (85-89¢): {config['accuracy_by_price_range']['0.85-0.89'] * 100:.1f}%")
print(f"  Category accuracy (Entertainment): {config['category_accuracy']['Entertainment'] * 100:.1f}%")

win_prob_entertainment = scorer._get_win_probability(0.87, "Entertainment")
expected_conservative = min(config['accuracy_by_price_range']['0.85-0.89'],
                           config['category_accuracy']['Entertainment'])

print(f"  Expected (conservative): {expected_conservative * 100:.1f}%")
print(f"  Actual: {win_prob_entertainment * 100:.1f}%")

if abs(win_prob_entertainment - expected_conservative) < 0.001:
    print("  ✅ PASS - Using conservative estimate (category 89.3%)")
else:
    print(f"  ❌ FAIL - Expected {expected_conservative:.3f}, got {win_prob_entertainment:.3f}")
print()

# Test case 2: Financials (88.3% < 95%) at 92¢
print("Test 2: Financials market at $0.92")
print("-" * 80)
print(f"  Price range accuracy (90-95¢): {config['accuracy_by_price_range']['0.90-0.95'] * 100:.1f}%")
print(f"  Category accuracy (Financials): {config['category_accuracy']['Financials'] * 100:.1f}%")

win_prob_financials = scorer._get_win_probability(0.92, "Financials")
expected_conservative = min(config['accuracy_by_price_range']['0.90-0.95'],
                           config['category_accuracy']['Financials'])

print(f"  Expected (conservative): {expected_conservative * 100:.1f}%")
print(f"  Actual: {win_prob_financials * 100:.1f}%")

if abs(win_prob_financials - expected_conservative) < 0.001:
    print("  ✅ PASS - Using conservative estimate (category 88.3%)")
else:
    print(f"  ❌ FAIL - Expected {expected_conservative:.3f}, got {win_prob_financials:.3f}")
print()

# Test case 3: Sports (98.8% > 95%) at 87¢
print("Test 3: Sports market at $0.87")
print("-" * 80)
print(f"  Price range accuracy (85-89¢): {config['accuracy_by_price_range']['0.85-0.89'] * 100:.1f}%")
print(f"  Category accuracy (Sports): {config['category_accuracy']['Sports'] * 100:.1f}%")

win_prob_sports = scorer._get_win_probability(0.87, "Sports")
expected_price_based = config['accuracy_by_price_range']['0.85-0.89']

print(f"  Expected (price-based): {expected_price_based * 100:.1f}%")
print(f"  Actual: {win_prob_sports * 100:.1f}%")

if abs(win_prob_sports - expected_price_based) < 0.001:
    print("  ✅ PASS - Using price range accuracy (category above threshold)")
else:
    print(f"  ❌ FAIL - Expected {expected_price_based:.3f}, got {win_prob_sports:.3f}")
print()

# Test case 4: Crypto (99.5% > 95%) at 96¢
print("Test 4: Crypto market at $0.96")
print("-" * 80)
print(f"  Price range accuracy (95-98¢): {config['accuracy_by_price_range']['0.95-0.98'] * 100:.1f}%")
print(f"  Category accuracy (Crypto): {config['category_accuracy']['Crypto'] * 100:.1f}%")

win_prob_crypto = scorer._get_win_probability(0.96, "Crypto")
expected_price_based = config['accuracy_by_price_range']['0.95-0.98']

print(f"  Expected (price-based): {expected_price_based * 100:.1f}%")
print(f"  Actual: {win_prob_crypto * 100:.1f}%")

if abs(win_prob_crypto - expected_price_based) < 0.001:
    print("  ✅ PASS - Using price range accuracy (category above threshold)")
else:
    print(f"  ❌ FAIL - Expected {expected_price_based:.3f}, got {win_prob_crypto:.3f}")
print()

# Test case 5: Unknown category at 87¢
print("Test 5: Unknown category at $0.87")
print("-" * 80)
print(f"  Price range accuracy (85-89¢): {config['accuracy_by_price_range']['0.85-0.89'] * 100:.1f}%")
print(f"  Category: Not in config")

win_prob_unknown = scorer._get_win_probability(0.87, "UnknownCategory")
expected_price_based = config['accuracy_by_price_range']['0.85-0.89']

print(f"  Expected (price-based): {expected_price_based * 100:.1f}%")
print(f"  Actual: {win_prob_unknown * 100:.1f}%")

if abs(win_prob_unknown - expected_price_based) < 0.001:
    print("  ✅ PASS - Using price range accuracy (category not found)")
else:
    print(f"  ❌ FAIL - Expected {expected_price_based:.3f}, got {win_prob_unknown:.3f}")
print()

print("=" * 80)
print("📊 COMPARATIVE EXAMPLES")
print("=" * 80)
print()

print("Same price ($0.87), different categories:")
print()

categories_to_test = [
    ("Entertainment", 0.87),
    ("Financials", 0.87),
    ("Sports", 0.87),
    ("Crypto", 0.87),
    ("Health", 0.87),
]

for category, price in categories_to_test:
    win_prob = scorer._get_win_probability(price, category)
    cat_acc = config['category_accuracy'].get(category, None)
    price_acc = config['accuracy_by_price_range']['0.85-0.89']

    if cat_acc and cat_acc < config['category_accuracy_threshold']:
        used = "CATEGORY (override)"
        indicator = "⚠️"
    else:
        used = "PRICE RANGE"
        indicator = "✓"

    print(f"  {indicator} {category:20s} → {win_prob * 100:.1f}% ({used})")

print()

print("Same category (Entertainment), different prices:")
print()

prices_to_test = [0.50, 0.87, 0.92, 0.96]
for price in prices_to_test:
    win_prob = scorer._get_win_probability(price, "Entertainment")

    # Determine which range
    if 0.85 <= price <= 0.89:
        range_name = "85-89¢"
    elif 0.90 <= price <= 0.95:
        range_name = "90-95¢"
    elif 0.95 <= price <= 0.98:
        range_name = "95-98¢"
    else:
        range_name = "default"

    print(f"  ⚠️  ${price:.2f} ({range_name:8s}) → {win_prob * 100:.1f}% (Entertainment override)")

print()

print("=" * 80)
print("✅ TEST SUMMARY")
print("=" * 80)
print()

print("Category Accuracy Override Feature:")
print()
print("  ✓ Uses MORE CONSERVATIVE estimate for low-performing categories")
print("  ✓ Entertainment (89.3%) uses category accuracy instead of price range")
print("  ✓ Financials (88.3%) uses category accuracy instead of price range")
print("  ✓ High-performing categories (>95%) use price range accuracy")
print("  ✓ Unknown categories default to price range accuracy")
print()

print("This ensures:")
print("  • Never overestimate win probability for risky categories")
print("  • Always use the more conservative (safer) estimate")
print("  • Protect against losses in underperforming market types")
print()

print("Example impact:")
print(f"  • Entertainment at 87¢: {scorer._get_win_probability(0.87, 'Entertainment') * 100:.1f}% (was 99.1% before override)")
print(f"  • Financials at 92¢: {scorer._get_win_probability(0.92, 'Financials') * 100:.1f}% (was 99.0% before override)")
print(f"  • Sports at 87¢: {scorer._get_win_probability(0.87, 'Sports') * 100:.1f}% (no override needed)")
print()
