"""
Decision Logger
Tracks every market evaluation and decision made by the bot
"""
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dataclasses import dataclass, asdict
from logger_setup import get_logger

logger = get_logger("decision_logger")


@dataclass
class MarketDecision:
    """Represents a decision made about a market"""
    # Market info
    ticker: str
    title: str
    category: str
    current_yes_price: float
    current_no_price: float
    time_to_settlement_hours: float

    # Evaluation
    model_accuracy: Optional[float]  # If we have data
    score: Optional[float]  # Expected ROI if scored

    # Decision
    decision: str  # 'bet' or 'skipped'
    skip_reason: Optional[str]  # If skipped
    bet_side: Optional[str]  # YES or NO if bet
    bet_amount: Optional[float]  # $ if bet
    bet_contracts: Optional[int]  # Contracts if bet

    # Metadata
    timestamp: str
    cycle_id: str

    # Outcome tracking (filled in later)
    settled: bool = False
    settled_at: Optional[str] = None
    outcome: Optional[str] = None  # 'YES' or 'NO'
    actual_pnl: Optional[float] = None
    would_have_won: Optional[bool] = None  # For missed opportunities


class DecisionLogger:
    """
    Logs all market evaluation decisions to JSON file

    Enables post-analysis of:
    - What markets were considered
    - Why markets were skipped
    - Missed opportunities
    - Decision patterns
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.decisions_file = os.path.join(data_dir, "decisions.json")

        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)

        # Current cycle decisions (in memory)
        self.current_cycle_decisions: List[MarketDecision] = []
        self.current_cycle_id: Optional[str] = None

        logger.info(f"DecisionLogger initialized - logging to {self.decisions_file}")

    def start_cycle(self) -> str:
        """Start a new decision cycle"""
        cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.current_cycle_id = cycle_id
        self.current_cycle_decisions = []
        logger.debug(f"Started decision cycle: {cycle_id}")
        return cycle_id

    def log_skipped(
        self,
        ticker: str,
        title: str,
        category: str,
        yes_price: float,
        no_price: float,
        time_to_settlement_hours: float,
        skip_reason: str,
        model_accuracy: Optional[float] = None,
        score: Optional[float] = None
    ) -> None:
        """Log a market that was skipped"""

        decision = MarketDecision(
            ticker=ticker,
            title=title,
            category=category,
            current_yes_price=yes_price,
            current_no_price=no_price,
            time_to_settlement_hours=time_to_settlement_hours,
            model_accuracy=model_accuracy,
            score=score,
            decision="skipped",
            skip_reason=skip_reason,
            bet_side=None,
            bet_amount=None,
            bet_contracts=None,
            timestamp=datetime.utcnow().isoformat(),
            cycle_id=self.current_cycle_id or "unknown"
        )

        self.current_cycle_decisions.append(decision)
        logger.debug(f"Logged skip: {ticker} - {skip_reason}")

    def log_bet(
        self,
        ticker: str,
        title: str,
        category: str,
        yes_price: float,
        no_price: float,
        time_to_settlement_hours: float,
        side: str,
        amount: float,
        contracts: int,
        score: float,
        model_accuracy: Optional[float] = None
    ) -> None:
        """Log a market where we placed a bet"""

        decision = MarketDecision(
            ticker=ticker,
            title=title,
            category=category,
            current_yes_price=yes_price,
            current_no_price=no_price,
            time_to_settlement_hours=time_to_settlement_hours,
            model_accuracy=model_accuracy,
            score=score,
            decision="bet",
            skip_reason=None,
            bet_side=side,
            bet_amount=amount,
            bet_contracts=contracts,
            timestamp=datetime.utcnow().isoformat(),
            cycle_id=self.current_cycle_id or "unknown"
        )

        self.current_cycle_decisions.append(decision)
        logger.info(f"Logged bet: {ticker} - {side} @ ${amount:.2f}")

    def end_cycle(self) -> None:
        """End current cycle and write decisions to file"""

        if not self.current_cycle_decisions:
            logger.debug("No decisions to log this cycle")
            return

        # Load existing decisions
        existing_decisions = self._load_decisions()

        # Add current cycle decisions
        for decision in self.current_cycle_decisions:
            existing_decisions.append(asdict(decision))

        # Write back
        self._save_decisions(existing_decisions)

        logger.info(f"Logged {len(self.current_cycle_decisions)} decisions for cycle {self.current_cycle_id}")

        # Reset
        self.current_cycle_decisions = []
        self.current_cycle_id = None

    def update_outcome(
        self,
        ticker: str,
        outcome: str,
        actual_pnl: float,
        settled_at: Optional[str] = None
    ) -> None:
        """
        Update decision with actual outcome after settlement

        Args:
            ticker: Market ticker
            outcome: 'YES' or 'NO'
            actual_pnl: Actual profit/loss
            settled_at: Settlement timestamp
        """

        decisions = self._load_decisions()
        updated = False

        # Find most recent bet decision for this ticker
        for decision in reversed(decisions):
            if decision['ticker'] == ticker and decision['decision'] == 'bet':
                decision['settled'] = True
                decision['settled_at'] = settled_at or datetime.utcnow().isoformat()
                decision['outcome'] = outcome
                decision['actual_pnl'] = actual_pnl
                updated = True
                break

        if updated:
            self._save_decisions(decisions)
            logger.info(f"Updated outcome for {ticker}: {outcome}, P&L: ${actual_pnl:+.2f}")
        else:
            logger.warning(f"No bet decision found for {ticker} to update")

    def mark_missed_opportunities(self, lookback_days: int = 1) -> int:
        """
        Mark skipped markets that settled profitably as missed opportunities

        This requires checking settlements and updating would_have_won field
        Returns number of missed opportunities found
        """

        decisions = self._load_decisions()

        # Get recent skipped decisions
        cutoff = datetime.utcnow()
        missed_count = 0

        for decision in decisions:
            # Only look at skipped markets
            if decision['decision'] != 'skipped':
                continue

            # Skip if already marked
            if decision.get('settled'):
                continue

            # TODO: Check if this market has settled
            # This would require calling Kalshi API to check market status
            # For now, we'll leave this as a placeholder
            # In production, this would be called periodically to update outcomes

        return missed_count

    def get_decisions_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get all decisions for a specific date"""

        decisions = self._load_decisions()
        date_str = target_date.strftime("%Y%m%d")

        # Filter by date
        return [
            d for d in decisions
            if d['cycle_id'].startswith(date_str)
        ]

    def get_decisions_since(self, since: datetime) -> List[Dict[str, Any]]:
        """Get all decisions since a timestamp"""

        decisions = self._load_decisions()
        since_str = since.isoformat()

        return [
            d for d in decisions
            if d['timestamp'] >= since_str
        ]

    def _load_decisions(self) -> List[Dict[str, Any]]:
        """Load decisions from file"""

        if not os.path.exists(self.decisions_file):
            return []

        try:
            with open(self.decisions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading decisions: {e}")
            return []

    def _save_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        """Save decisions to file"""

        try:
            with open(self.decisions_file, 'w') as f:
                json.dump(decisions, f, indent=2)
            logger.debug(f"Saved {len(decisions)} total decisions to {self.decisions_file}")
        except Exception as e:
            logger.error(f"Error saving decisions: {e}")
