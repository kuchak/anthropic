"""
Report Generator
Creates daily summary reports and analyzes decision patterns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
from logger_setup import get_logger
from decision_logger import DecisionLogger

logger = get_logger("report_generator")


class ReportGenerator:
    """
    Generates comprehensive reports from decision logs

    Reports include:
    - Market scanning statistics
    - Skip reason breakdown
    - Bet performance
    - Missed opportunities analysis
    """

    def __init__(self, decision_logger: DecisionLogger):
        self.decision_logger = decision_logger

    def generate_daily_report(self, target_date: Optional[date] = None) -> str:
        """
        Generate comprehensive daily summary report

        Args:
            target_date: Date to report on (defaults to today UTC)

        Returns:
            Formatted report string
        """

        if target_date is None:
            # Use UTC date, not local date!
            # This prevents timezone bugs where local date != UTC date
            from datetime import timezone
            target_date = datetime.now(timezone.utc).date()

        logger.info(f"Generating daily report for {target_date}")

        # Get all decisions for this date
        decisions = self.decision_logger.get_decisions_for_date(target_date)

        if not decisions:
            return self._format_empty_report(target_date)

        # Analyze decisions
        stats = self._analyze_decisions(decisions)

        # Format report
        report = self._format_report(target_date, stats, decisions)

        return report

    def generate_period_report(self, days: int = 7) -> str:
        """Generate report for the last N days"""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Generating {days}-day report")

        # Get decisions in period
        decisions = self.decision_logger.get_decisions_since(start_date)

        if not decisions:
            return f"No trading activity in the last {days} days"

        # Analyze
        stats = self._analyze_decisions(decisions)

        # Format
        report = self._format_period_report(days, stats, decisions)

        return report

    def _analyze_decisions(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze decisions and compute statistics"""

        stats = {
            'total_markets': len(decisions),
            'markets_bet': 0,
            'markets_skipped': 0,
            'skip_reasons': Counter(),
            'bets_by_side': Counter(),
            'total_bet_amount': 0.0,
            'total_contracts': 0,
            'categories_seen': Counter(),
            'avg_score': None,
            'settled_bets': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'win_rate': None,
            'missed_opportunities': []
        }

        scores = []

        for decision in decisions:
            # Category tracking
            stats['categories_seen'][decision['category']] += 1

            # Decision type
            if decision['decision'] == 'bet':
                stats['markets_bet'] += 1
                stats['bets_by_side'][decision['bet_side']] += 1
                stats['total_bet_amount'] += decision['bet_amount'] or 0
                stats['total_contracts'] += decision['bet_contracts'] or 0

                if decision.get('score'):
                    scores.append(decision['score'])

                # Settlement tracking
                if decision.get('settled'):
                    stats['settled_bets'] += 1
                    pnl = decision.get('actual_pnl', 0)
                    stats['total_pnl'] += pnl

                    if pnl > 0:
                        stats['wins'] += 1
                    elif pnl < 0:
                        stats['losses'] += 1

            elif decision['decision'] == 'skipped':
                stats['markets_skipped'] += 1
                skip_reason = decision.get('skip_reason', 'unknown')
                stats['skip_reasons'][skip_reason] += 1

                # Check if this was a missed opportunity
                if decision.get('settled') and decision.get('would_have_won'):
                    stats['missed_opportunities'].append(decision)

        # Compute averages
        if scores:
            stats['avg_score'] = sum(scores) / len(scores)

        if stats['settled_bets'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['settled_bets']) * 100

        return stats

    def _format_report(
        self,
        target_date: date,
        stats: Dict[str, Any],
        decisions: List[Dict[str, Any]]
    ) -> str:
        """Format daily report"""

        lines = []
        lines.append("=" * 80)
        lines.append(f"DAILY TRADING REPORT - {target_date.strftime('%Y-%m-%d')}")
        lines.append("=" * 80)
        lines.append("")

        # Overview
        lines.append("📊 MARKET SCANNING")
        lines.append("-" * 80)
        lines.append(f"Total markets evaluated: {stats['total_markets']}")
        lines.append(f"Markets bet on: {stats['markets_bet']}")
        lines.append(f"Markets skipped: {stats['markets_skipped']}")
        lines.append("")

        # Categories
        if stats['categories_seen']:
            lines.append("📁 Categories Evaluated:")
            for category, count in stats['categories_seen'].most_common(10):
                lines.append(f"   {category}: {count}")
            lines.append("")

        # Skip reasons breakdown
        if stats['skip_reasons']:
            lines.append("⏭️  SKIP REASONS BREAKDOWN")
            lines.append("-" * 80)
            for reason, count in stats['skip_reasons'].most_common():
                pct = (count / stats['markets_skipped']) * 100 if stats['markets_skipped'] > 0 else 0
                lines.append(f"   {reason}: {count} ({pct:.1f}%)")
            lines.append("")

        # Betting activity
        if stats['markets_bet'] > 0:
            lines.append("💰 BETTING ACTIVITY")
            lines.append("-" * 80)
            lines.append(f"Total amount bet: ${stats['total_bet_amount']:.2f}")
            lines.append(f"Total contracts: {stats['total_contracts']}")
            if stats['avg_score']:
                lines.append(f"Average expected ROI: {stats['avg_score']:.1f}%")
            lines.append("")

            lines.append("Side breakdown:")
            for side, count in stats['bets_by_side'].items():
                lines.append(f"   {side}: {count}")
            lines.append("")

        # Performance
        if stats['settled_bets'] > 0:
            lines.append("📈 PERFORMANCE")
            lines.append("-" * 80)
            lines.append(f"Settled bets: {stats['settled_bets']}")
            lines.append(f"Wins: {stats['wins']}")
            lines.append(f"Losses: {stats['losses']}")
            lines.append(f"Win rate: {stats['win_rate']:.1f}%")
            lines.append(f"Total P&L: ${stats['total_pnl']:+.2f}")
            lines.append("")

        # Missed opportunities
        if stats['missed_opportunities']:
            lines.append("🎯 TOP MISSED OPPORTUNITIES")
            lines.append("-" * 80)
            lines.append("Markets that were skipped but would have been profitable:")
            lines.append("")

            # Sort by potential profit
            missed = sorted(
                stats['missed_opportunities'],
                key=lambda x: x.get('actual_pnl', 0),
                reverse=True
            )[:5]  # Top 5

            for i, opp in enumerate(missed, 1):
                lines.append(f"{i}. {opp['ticker']}")
                lines.append(f"   {opp['title']}")
                lines.append(f"   Skipped reason: {opp['skip_reason']}")
                lines.append(f"   Price: YES ${opp['current_yes_price']:.2f}, NO ${opp['current_no_price']:.2f}")
                lines.append(f"   Outcome: {opp['outcome']}")
                lines.append(f"   Would have won: ${opp.get('actual_pnl', 0):+.2f}")
                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_period_report(
        self,
        days: int,
        stats: Dict[str, Any],
        decisions: List[Dict[str, Any]]
    ) -> str:
        """Format multi-day period report"""

        lines = []
        lines.append("=" * 80)
        lines.append(f"{days}-DAY TRADING REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Overview
        lines.append(f"📊 Total markets evaluated: {stats['total_markets']}")
        lines.append(f"   Markets bet on: {stats['markets_bet']}")
        lines.append(f"   Markets skipped: {stats['markets_skipped']}")
        lines.append(f"   Total amount bet: ${stats['total_bet_amount']:.2f}")
        lines.append("")

        # Performance
        if stats['settled_bets'] > 0:
            lines.append("📈 PERFORMANCE")
            lines.append("-" * 80)
            lines.append(f"Settled bets: {stats['settled_bets']}")
            lines.append(f"Win rate: {stats['win_rate']:.1f}% ({stats['wins']}W-{stats['losses']}L)")
            lines.append(f"Total P&L: ${stats['total_pnl']:+.2f}")
            lines.append("")

        # Skip reasons
        if stats['skip_reasons']:
            lines.append("⏭️  Most Common Skip Reasons:")
            for reason, count in stats['skip_reasons'].most_common(5):
                lines.append(f"   {reason}: {count}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_empty_report(self, target_date: date) -> str:
        """Format report for date with no activity"""

        lines = []
        lines.append("=" * 80)
        lines.append(f"DAILY TRADING REPORT - {target_date.strftime('%Y-%m-%d')}")
        lines.append("=" * 80)
        lines.append("")
        lines.append("No trading activity recorded for this date")
        lines.append("=" * 80)

        return "\n".join(lines)

    def export_decisions_csv(self, output_file: str, days: int = 30) -> None:
        """Export recent decisions to CSV for external analysis"""

        import csv

        # Get decisions
        start_date = datetime.utcnow() - timedelta(days=days)
        decisions = self.decision_logger.get_decisions_since(start_date)

        # Write CSV
        with open(output_file, 'w', newline='') as f:
            if not decisions:
                logger.info("No decisions to export")
                return

            # Get all possible fields
            fieldnames = list(decisions[0].keys())

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(decisions)

        logger.info(f"Exported {len(decisions)} decisions to {output_file}")
