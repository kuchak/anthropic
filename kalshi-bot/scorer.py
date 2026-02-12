"""
Opportunity Scorer
Ranks trading opportunities by expected profit
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from logger_setup import get_logger
from models import Market

logger = get_logger("scorer")


@dataclass
class ScoredOpportunity:
    """
    A trading opportunity with calculated metrics

    Attributes:
        market: The underlying market
        side: "YES" or "NO" - which side to buy
        entry_price: Price we'd pay to enter
        win_probability: Our estimated probability of winning (from backtests)
        expected_profit: Expected profit per contract
        expected_roi: Expected return on investment (%)
        rank_score: Final ranking score (higher = better)
        time_to_settlement_hours: Hours until settlement
    """
    market: Market
    side: str
    entry_price: float
    win_probability: float
    expected_profit: float
    expected_roi: float
    rank_score: float
    time_to_settlement_hours: float

    def __repr__(self) -> str:
        return (
            f"ScoredOpportunity("
            f"ticker={self.market.ticker}, "
            f"side={self.side}, "
            f"entry_price=${self.entry_price:.2f}, "
            f"expected_roi={self.expected_roi:.1f}%, "
            f"rank_score={self.rank_score:.2f})"
        )


class Scorer:
    """
    Scores and ranks trading opportunities

    Uses backtest accuracy data to calculate:
    - Win probability
    - Expected profit
    - Expected ROI
    - Rank score

    Key insight from backtests:
    - 85-89¢ contracts: 91.2% accuracy (11 wins, 1 loss, 91.7% avg profit)
    - 90-95¢ contracts: 89.4% accuracy (84/94 wins, 89.4% avg profit)
    - Overall 85-98¢: ~90% accuracy
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Load accuracy data from config
        self.accuracy_by_price_range = config.get('accuracy_by_price_range', {})
        self.default_accuracy = config.get('default_accuracy', 0.90)

        logger.info("Scorer initialized")
        logger.info(f"  Default accuracy: {self.default_accuracy * 100:.1f}%")
        logger.info(f"  Price range accuracies: {len(self.accuracy_by_price_range)} ranges configured")

    def score_markets(self, markets: List[Market]) -> List[ScoredOpportunity]:
        """
        Score all markets and return ranked opportunities

        Args:
            markets: List of markets to score

        Returns:
            List of scored opportunities, sorted by rank (best first)
        """
        opportunities = []

        for market in markets:
            # Score both YES and NO sides
            yes_opp = self._score_market_side(market, "YES")
            no_opp = self._score_market_side(market, "NO")

            # Add valid opportunities
            if yes_opp and yes_opp.expected_roi > 0:
                opportunities.append(yes_opp)

            if no_opp and no_opp.expected_roi > 0:
                opportunities.append(no_opp)

        # Sort by rank score (descending)
        opportunities.sort(key=lambda x: x.rank_score, reverse=True)

        logger.debug(f"Scored {len(markets)} markets → {len(opportunities)} valid opportunities")

        return opportunities

    def _score_market_side(self, market: Market, side: str) -> Optional[ScoredOpportunity]:
        """
        Score one side of a market (YES or NO)

        Args:
            market: Market to score
            side: "YES" or "NO"

        Returns:
            ScoredOpportunity or None if invalid
        """
        # Get entry price
        entry_price = market.best_yes_price if side == "YES" else market.best_no_price

        # Validate price is in target range
        if not (self.config['min_contract_price'] <= entry_price <= self.config['max_contract_price']):
            return None

        # Calculate win probability based on price range
        win_probability = self._get_win_probability(entry_price)

        # Calculate expected profit
        # Win: Profit = $1.00 - entry_price
        # Loss: Loss = entry_price
        # Expected profit = P(win) * profit - P(loss) * loss
        profit_if_win = 1.0 - entry_price
        loss_if_loss = entry_price

        expected_profit = (win_probability * profit_if_win) - ((1 - win_probability) * loss_if_loss)
        expected_roi = (expected_profit / entry_price) * 100 if entry_price > 0 else 0

        # Calculate rank score
        # Higher score = better opportunity
        # Factors:
        # 1. Expected ROI (primary)
        # 2. Time to settlement (prefer shorter)
        # 3. Win probability (prefer higher confidence)

        time_to_settlement_hours = market.time_to_settlement_minutes / 60

        # Normalize time factor (prefer 1-3 hours, penalize very short or very long)
        if time_to_settlement_hours < 1:
            time_factor = 0.7  # Too risky - not much time to analyze
        elif time_to_settlement_hours < 3:
            time_factor = 1.0  # Sweet spot
        elif time_to_settlement_hours < 6:
            time_factor = 0.9  # Still good
        else:
            time_factor = 0.8  # Capital tied up longer

        # Confidence boost for high-accuracy ranges
        confidence_factor = 1.0 + (win_probability - self.default_accuracy) * 2

        # Final rank score
        rank_score = expected_roi * time_factor * confidence_factor

        return ScoredOpportunity(
            market=market,
            side=side,
            entry_price=entry_price,
            win_probability=win_probability,
            expected_profit=expected_profit,
            expected_roi=expected_roi,
            rank_score=rank_score,
            time_to_settlement_hours=time_to_settlement_hours
        )

    def _get_win_probability(self, price: float) -> float:
        """
        Get win probability based on price range

        Uses backtest accuracy data from config

        Args:
            price: Contract price (0.0 - 1.0)

        Returns:
            Win probability (0.0 - 1.0)
        """
        # Check if we have specific accuracy for this price range
        for price_range, accuracy in self.accuracy_by_price_range.items():
            # Parse range like "0.85-0.89" or "0.90-0.95"
            if '-' in price_range:
                min_price, max_price = map(float, price_range.split('-'))
                if min_price <= price <= max_price:
                    return accuracy

        # Default to overall accuracy
        return self.default_accuracy

    def get_top_opportunities(self, markets: List[Market], limit: int = 10) -> List[ScoredOpportunity]:
        """
        Get top N trading opportunities

        Args:
            markets: List of markets to score
            limit: Maximum number of opportunities to return

        Returns:
            Top opportunities by rank score
        """
        all_opportunities = self.score_markets(markets)
        return all_opportunities[:limit]

    def get_stats(self, opportunities: List[ScoredOpportunity]) -> Dict[str, Any]:
        """
        Get statistics about scored opportunities

        Args:
            opportunities: List of scored opportunities

        Returns:
            Dictionary of statistics
        """
        if not opportunities:
            return {
                'total_opportunities': 0,
                'avg_expected_roi': 0,
                'avg_win_probability': 0,
                'avg_time_to_settlement_hours': 0
            }

        return {
            'total_opportunities': len(opportunities),
            'avg_expected_roi': sum(o.expected_roi for o in opportunities) / len(opportunities),
            'avg_win_probability': sum(o.win_probability for o in opportunities) / len(opportunities),
            'avg_time_to_settlement_hours': sum(o.time_to_settlement_hours for o in opportunities) / len(opportunities),
            'best_roi': max(o.expected_roi for o in opportunities),
            'worst_roi': min(o.expected_roi for o in opportunities),
        }
