"""
Analyze success rates by category for events that crossed 90%
Success rate = % of 90%+ predictions that settled correctly
"""

import csv
from collections import defaultdict

# Read the comprehensive crossed 90% file
with open('comprehensive_crossed_90_detailed.csv', 'r') as f:
    reader = csv.DictReader(f)

    category_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'wrong': 0})

    for row in reader:
        category = row['Category']
        prediction = row['Prediction Correct']

        category_stats[category]['total'] += 1

        if prediction == 'CORRECT':
            category_stats[category]['correct'] += 1
        elif prediction == 'WRONG':
            category_stats[category]['wrong'] += 1

# Calculate success rates and sort
results = []
for category, stats in category_stats.items():
    total = stats['total']
    correct = stats['correct']
    wrong = stats['wrong']
    success_rate = (correct / total * 100) if total > 0 else 0

    results.append({
        'category': category,
        'total_crossed_90': total,
        'correct': correct,
        'wrong': wrong,
        'success_rate': success_rate
    })

# Sort by success rate descending
results.sort(key=lambda x: x['success_rate'], reverse=True)

# Print results
print("=" * 80)
print("SUCCESS RATE BY CATEGORY")
print("(Events that crossed 90% and settled correctly)")
print("=" * 80)
print()

for i, r in enumerate(results, 1):
    print(f"{i:2d}. {r['category']:30s} {r['success_rate']:5.1f}%   ({r['correct']:5d} / {r['total_crossed_90']:5d})   [{r['wrong']:4d} wrong]")

print()
print("=" * 80)
print(f"OVERALL: {sum(r['correct'] for r in results)} / {sum(r['total_crossed_90'] for r in results)} = {sum(r['correct'] for r in results) / sum(r['total_crossed_90'] for r in results) * 100:.1f}%")
print("=" * 80)
